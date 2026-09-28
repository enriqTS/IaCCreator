"""Step Functions Batch connections submit generated jobs synchronously."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_batch import batch_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsBatchConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate
from tests.test_step_functions_ecs_connections import architecture as ecs_architecture


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.BATCH, None, {})
    )


def test_synchronous_task_and_scoped_policy_generated():
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        job_name="report-job", array_size=2, job_attempts=3
    )
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(
        value for path, value in tree.items() if path.endswith("/batch_tasks.tf")
    )
    policy = next(
        value for path, value in tree.items() if path.endswith("/batch_tasks_policy.tf")
    )
    generated = "\n".join(tree.values())
    assert "definition = local.batch_workflow_definition" in machine
    assert "local.batch_tasks_valid" in machine
    assert "batch:submitJob.sync" in task
    assert 'JobName = "report-job"' in task
    assert "ArrayProperties" in task and "RetryStrategy" in task
    assert "var.workflow_batch_queue_0_arn" in task
    assert "var.workflow_batch_definition_0_arn" in task
    assert "batch:SubmitJob" in policy
    assert "batch:DescribeJobs" in policy and "batch:TerminateJob" in policy
    assert "events:PutTargets" in policy
    assert "StepFunctionsGetEventsForBatchJobsRule" in policy
    assert "module.target-resource.job_queue_arn" in generated
    assert "module.batch-job.job_definition_arn" in generated
    assert generate(payload) == tree


def test_missing_role_or_job_definition_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = ""
    with pytest.raises(InvalidConnectionConfigError, match="execution role ARN"):
        generate(payload)
    payload = architecture()
    payload["connections"][0]["connection_config"]["job_definition_name"] = "missing"
    with pytest.raises(InvalidConnectionConfigError, match="job definition node"):
        generate(payload)


def test_managed_batch_compute_environment_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["batch_compute_environment_type"] = "MANAGED"
    with pytest.raises(
        InvalidConnectionConfigError, match="unmanaged compute environment"
    ):
        generate(payload)


def test_invalid_batch_settings_rejected():
    for settings in (
        {"array_size": 1},
        {"array_size": 10001},
        {"job_attempts": 0},
        {"job_attempts": 11},
    ):
        with pytest.raises(ValidationError):
            StepFunctionsBatchConfig(job_definition_name="batch-job", **settings)


def test_conflicting_state_bindings_rejected():
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"]["job_name"] = "other-job"
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_multiple_batch_states_share_one_workflow_policy():
    payload = architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "First",
            "States": {
                "First": {"Type": "Pass", "Next": "Second"},
                "Second": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"]["state_name"] = "First"
    second = deepcopy(payload["connections"][0])
    second["connection_config"].update(state_name="Second", job_name="other-job")
    payload["connections"].append(second)
    tree = generate(payload)
    task = next(
        value for path, value in tree.items() if path.endswith("/batch_tasks.tf")
    )
    assert "First = {" in task and "Second = {" in task
    assert sum(path.endswith("/batch_tasks_policy.tf") for path in tree) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_batch_and_ecs_states_compose_in_any_connection_order():
    payload = architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Run",
            "States": {
                "Run": {"Type": "Pass", "Next": "Job"},
                "Job": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"]["state_name"] = "Job"
    ecs_payload = ecs_architecture()
    task = deepcopy(ecs_payload["resources"][1])
    task.update(id="ecs", name="ecs-task")
    payload["resources"].append(task)
    connection = deepcopy(ecs_payload["connections"][0])
    connection.update(
        source="source-resource", source_id="src", target="ecs-task", target_id="ecs"
    )
    connection["connection_config"] = {"state_name": "Run"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    batch = next(
        value for path, value in tree.items() if path.endswith("/batch_tasks.tf")
    )
    assert "local.ecs_workflow_definition" in batch
    assert "local.ecs_tasks_valid" in machine
    assert "local.batch_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_batch_and_ecs_cannot_replace_the_same_state():
    payload = architecture()
    ecs_payload = ecs_architecture()
    task = deepcopy(ecs_payload["resources"][1])
    task.update(id="ecs", name="ecs-task")
    payload["resources"].append(task)
    connection = deepcopy(ecs_payload["connections"][0])
    connection.update(
        source="source-resource",
        source_id="src",
        target="ecs-task",
        target_id="ecs",
    )
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="multiple task connections"):
        generate(payload)


def test_batch_task_preserves_transition_and_data_path(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Job",
        "States": {
            "Job": {
                "Type": "Pass",
                "Next": "Done",
                "ResultPath": "$.job",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    content += (
        batch_workflow_locals(
            {
                "Job": {
                    "JobName": "report",
                    "JobQueue": Expr('"queue-arn"'),
                    "JobDefinition": Expr('"definition-arn"'),
                    "RetryStrategy": {"Attempts": 3},
                }
            },
            False,
            False,
            False,
        )
        .replace('data "aws_partition" "batch_tasks" {}\n', "")
        .replace("data.aws_partition.batch_tasks.partition", '"aws"')
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.batch_tasks_valid, workflow = jsondecode(local.batch_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    state = output["workflow"]["States"]["Job"]
    assert state["Resource"] == "arn:aws:states:::batch:submitJob.sync"
    assert state["Next"] == "Done"
    assert state["ResultPath"] == "$.job"
    assert "Result" not in state
    assert state["Parameters"]["RetryStrategy"] == {"Attempts": 3}


@needs_terraform
def test_step_functions_batch_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
