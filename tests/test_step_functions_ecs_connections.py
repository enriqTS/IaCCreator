"""Step Functions ECS connections create synchronous Fargate Task states."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_ecs import ecs_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsEcsConfig
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
from tests.test_step_functions_lambda_connections import (
    architecture as lambda_architecture,
)
from tests.test_step_functions_lambda_connections import (
    mixed_architecture as lambda_secret_architecture,
)


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.ECS, None, {})
    )


def test_fargate_task_and_scoped_policy_generated():
    tree = generate(architecture())
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(value for path, value in tree.items() if path.endswith("/ecs_tasks.tf"))
    policy = next(
        value for path, value in tree.items() if path.endswith("/ecs_tasks_policy.tf")
    )
    generated = "\n".join(tree.values())
    assert "definition = local.ecs_workflow_definition" in machine
    assert "local.ecs_tasks_valid" in machine
    assert "ecs:runTask.sync" in task
    assert 'LaunchType = "FARGATE"' in task
    assert "AwsvpcConfiguration" in task
    assert "var.workflow_ecs_0_subnet_ids" in task
    assert "ecs:RunTask" in policy
    assert "ecs:DescribeTasks" in policy
    assert "ecs:StopTask" in policy
    assert "events:PutTargets" in policy
    assert "StepFunctionsGetEventsForECSTaskRule" in policy
    assert "iam:PassRole" in policy
    assert "ecs:cluster" in policy
    assert "var.workflow_ecs_0_task_definition_arn" in policy
    assert "var.workflow_ecs_0_task_role_arn" in policy
    assert "module.target-resource.task_definition_arn" in generated
    assert "module.target-resource.task_role_arn" in generated
    assert generate(architecture()) == tree


def test_missing_network_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["subnet_ids"] = []
    with pytest.raises(InvalidConnectionConfigError, match="at least one task subnet"):
        generate(payload)


def test_missing_workflow_role_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = ""
    with pytest.raises(InvalidConnectionConfigError, match="execution role ARN"):
        generate(payload)


def test_invalid_task_count_rejected():
    with pytest.raises(ValidationError):
        StepFunctionsEcsConfig(task_count=0)
    with pytest.raises(ValidationError):
        StepFunctionsEcsConfig(task_count=11)


def test_conflicting_state_bindings_rejected():
    payload = architecture()
    second = deepcopy(payload["resources"][1])
    second.update(id="second", name="other-ecs")
    payload["resources"].append(second)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="other-ecs", target_id="second")
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_same_state_with_different_counts_rejected():
    payload = architecture()
    connection = deepcopy(payload["connections"][0])
    connection["connection_config"] = {"task_count": 2}
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_ecs_and_lambda_states_compose():
    payload = architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Invoke",
            "States": {
                "Invoke": {"Type": "Pass", "Next": "Run"},
                "Run": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"] = {"state_name": "Run"}
    lambda_payload = lambda_architecture()
    function = deepcopy(lambda_payload["resources"][1])
    function.update(id="lambda", name="lambda-task")
    payload["resources"].append(function)
    connection = deepcopy(lambda_payload["connections"][0])
    connection.update(
        source="source-resource",
        source_id="src",
        target="lambda-task",
        target_id="lambda",
    )
    connection["connection_config"] = {"state_name": "Invoke"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(value for path, value in tree.items() if path.endswith("/ecs_tasks.tf"))
    assert "local.lambda_workflow_definition" in task
    assert "local.lambda_tasks_valid" in machine
    assert "local.ecs_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_ecs_lambda_and_secret_states_compose():
    payload = lambda_secret_architecture()
    workflow = json.loads(payload["resources"][0]["config"]["definition"])
    workflow["States"]["Invoke"] = {"Type": "Pass", "Next": "Run"}
    workflow["States"]["Run"] = {"Type": "Pass", "End": True}
    payload["resources"][0]["config"]["definition"] = json.dumps(workflow)
    ecs = deepcopy(architecture()["resources"][1])
    ecs.update(id="ecs", name="ecs-task")
    payload["resources"].append(ecs)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource",
        source_id="src",
        target="ecs-task",
        target_id="ecs",
    )
    connection["connection_config"] = {"state_name": "Run"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    assert "local.ecs_workflow_definition" in machine
    assert "local.lambda_tasks_valid" in machine
    assert "local.secret_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_ecs_task_keeps_transitions_and_network_settings(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Run",
        "States": {
            "Run": {
                "Type": "Pass",
                "Next": "Done",
                "ResultPath": "$.task",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    bindings = {
        "Run": {
            "cluster": Expr('"arn:aws:ecs:us-east-1:123456789012:cluster/example"'),
            "definition": Expr(
                '"arn:aws:ecs:us-east-1:123456789012:task-definition/example:1"'
            ),
            "subnets": ["subnet-12345678"],
            "security_groups": ["sg-12345678"],
            "assign_public_ip": False,
            "count": 2,
        }
    }
    content += (
        ecs_workflow_locals(bindings, False, False)
        .replace('data "aws_partition" "ecs_tasks" {}\n', "")
        .replace("data.aws_partition.ecs_tasks.partition", '"aws"')
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.ecs_tasks_valid, workflow = jsondecode(local.ecs_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    state = output["workflow"]["States"]["Run"]
    assert state["Resource"] == "arn:aws:states:::ecs:runTask.sync"
    assert state["Next"] == "Done"
    assert state["ResultPath"] == "$.task"
    assert "Result" not in state
    assert state["Parameters"]["Count"] == 2
    assert state["Parameters"]["NetworkConfiguration"]["AwsvpcConfiguration"] == {
        "AssignPublicIp": "DISABLED",
        "SecurityGroups": ["sg-12345678"],
        "Subnets": ["subnet-12345678"],
    }


@needs_terraform
def test_step_functions_ecs_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
