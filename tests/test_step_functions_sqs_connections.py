"""Step Functions SQS connections send state input to generated queues."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_sqs import sqs_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsSqsConfig
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
from tests.test_kms_access_integration import add_key
from tests.test_step_functions_sns_connections import architecture as sns_architecture


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.SQS, None, {})
    )


def test_send_task_and_queue_scoped_policy_generated():
    tree = generate(architecture())
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(value for path, value in tree.items() if path.endswith("/sqs_tasks.tf"))
    policy = next(
        value for path, value in tree.items() if path.endswith("/sqs_tasks_policy.tf")
    )
    generated = "\n".join(tree.values())
    assert "definition = local.sqs_workflow_definition" in machine
    assert "local.sqs_tasks_valid" in machine
    assert "sqs:sendMessage" in task
    assert '"MessageBody.$" = "States.JsonToString($)"' in task
    assert "var.workflow_sqs_queue_0_url" in task
    assert "sqs:SendMessage" in policy
    assert "var.workflow_sqs_queue_0_arn" in policy
    assert "kms:Decrypt" not in policy
    assert "module.target-resource.queue_url" in generated
    assert "module.target-resource.queue_arn" in generated
    assert generate(architecture()) == tree


def test_constant_message_and_multiple_states_aggregate():
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
    payload["connections"][0]["connection_config"] = {
        "state_name": "First",
        "message": "ready",
    }
    second = deepcopy(payload["connections"][0])
    second["connection_config"] = {"state_name": "Second"}
    payload["connections"].append(second)
    tree = generate(payload)
    task = next(value for path, value in tree.items() if path.endswith("/sqs_tasks.tf"))
    assert 'MessageBody = "ready"' in task
    assert '"MessageBody.$" = "States.JsonToString($)"' in task
    assert sum(path.endswith("/sqs_tasks_policy.tf") for path in tree) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_multiple_queues_and_one_encrypted_target_share_scoped_policy():
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
    payload["connections"][0]["connection_config"] = {"state_name": "First"}
    queue = deepcopy(payload["resources"][1])
    queue.update(id="second", name="z-queue")
    queue["config"].update(queue_name="z-queue", kms_master_key_id="alias/second-key")
    payload["resources"].append(queue)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="z-queue", target_id="second")
    connection["connection_config"] = {"state_name": "Second"}
    payload["connections"].append(connection)
    tree = generate(payload)
    task = next(value for path, value in tree.items() if path.endswith("/sqs_tasks.tf"))
    policy = next(
        value for path, value in tree.items() if path.endswith("/sqs_tasks_policy.tf")
    )
    assert "var.workflow_sqs_queue_0_url" in task
    assert "var.workflow_sqs_queue_1_url" in task
    assert "var.workflow_sqs_queue_0_arn" in policy
    assert "var.workflow_sqs_queue_1_arn" in policy
    assert "data.aws_kms_key.workflow_sqs_key_1_arn.arn" in policy
    assert "workflow_sqs_key_0_arn" not in policy
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_fifo_queue_requires_name_and_group_and_generates_deduplication_id():
    payload = architecture()
    payload["resources"][1]["config"]["fifo_queue"] = True
    with pytest.raises(InvalidConnectionConfigError, match="must end in .fifo"):
        generate(payload)
    payload["resources"][1]["config"]["queue_name"] = "messages.fifo"
    with pytest.raises(InvalidConnectionConfigError, match="message group ID"):
        generate(payload)
    payload["connections"][0]["connection_config"] = {"message_group_id": "orders"}
    task = next(
        value
        for path, value in generate(payload).items()
        if path.endswith("/sqs_tasks.tf")
    )
    assert 'MessageGroupId = "orders"' in task
    assert '"MessageDeduplicationId.$" = "States.UUID()"' in task
    payload["resources"][1]["config"]["content_based_deduplication"] = True
    task = next(
        value
        for path, value in generate(payload).items()
        if path.endswith("/sqs_tasks.tf")
    )
    assert "MessageDeduplicationId" not in task


def test_standard_queue_rejects_fifo_settings_and_empty_message():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"message_group_id": "orders"}
    with pytest.raises(InvalidConnectionConfigError, match="require a FIFO queue"):
        generate(payload)
    payload["connections"][0]["connection_config"] = {"message": ""}
    with pytest.raises(InvalidConnectionConfigError, match="must contain"):
        generate(payload)


def test_missing_role_placeholder_and_conflicting_state_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = ""
    with pytest.raises(InvalidConnectionConfigError, match="execution role ARN"):
        generate(payload)
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"state_name": "Missing"}
    with pytest.raises(
        InvalidConnectionConfigError, match="existing top-level Pass state"
    ):
        generate(payload)
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"] = {"message": "different"}
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_invalid_group_id_rejected():
    with pytest.raises(ValidationError):
        StepFunctionsSqsConfig(message_group_id="bad group")


@pytest.mark.parametrize("managed", [False, True])
def test_encrypted_queues_grant_scoped_kms_access(managed):
    payload = architecture()
    if managed:
        add_key(payload)
    else:
        payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external-key"
    tree = generate(payload)
    policy = next(
        value for path, value in tree.items() if path.endswith("/sqs_tasks_policy.tf")
    )
    assert "kms:Decrypt" in policy and "kms:GenerateDataKey" in policy
    if managed:
        assert "var.workflow_sqs_key_0_arn" in policy
        assert "module.encryption-key.key_arn" in "\n".join(tree.values())
    else:
        assert "data.aws_kms_key.workflow_sqs_key_0_arn.arn" in policy
        assert "module.target-resource.kms_access_key_id" in "\n".join(tree.values())


def test_sns_and_sqs_states_compose_in_any_order():
    payload = sns_architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Notify",
            "States": {
                "Notify": {"Type": "Pass", "Next": "Queue"},
                "Queue": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"] = {"state_name": "Notify"}
    queue = deepcopy(architecture()["resources"][1])
    queue.update(id="queue", name="tasks")
    payload["resources"].append(queue)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource", source_id="src", target="tasks", target_id="queue"
    )
    connection["connection_config"] = {"state_name": "Queue"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(value for path, value in tree.items() if path.endswith("/sqs_tasks.tf"))
    assert "local.sns_workflow_definition" in task
    assert "local.sns_tasks_valid" in machine
    assert "local.sqs_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_sns_and_sqs_cannot_replace_the_same_state():
    payload = sns_architecture()
    queue = deepcopy(architecture()["resources"][1])
    queue.update(id="queue", name="tasks")
    payload["resources"].append(queue)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource", source_id="src", target="tasks", target_id="queue"
    )
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="multiple task connections"):
        generate(payload)


def test_sqs_task_preserves_transition_and_data_path(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Queue",
        "States": {
            "Queue": {
                "Type": "Pass",
                "Next": "Done",
                "ResultPath": "$.sent",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    content += (
        sqs_workflow_locals(
            {
                "Queue": {
                    "QueueUrl": Expr('"queue-url"'),
                    "MessageBody.$": "States.JsonToString($)",
                }
            },
            False,
            False,
            False,
            False,
            False,
        )
        .replace('data "aws_partition" "sqs_tasks" {}\n', "")
        .replace("data.aws_partition.sqs_tasks.partition", '"aws"')
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.sqs_tasks_valid, workflow = jsondecode(local.sqs_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    state = output["workflow"]["States"]["Queue"]
    assert state["Resource"] == "arn:aws:states:::sqs:sendMessage"
    assert state["Next"] == "Done"
    assert state["ResultPath"] == "$.sent"
    assert "Result" not in state
    assert state["Parameters"]["MessageBody.$"] == "States.JsonToString($)"


@needs_terraform
@pytest.mark.parametrize("encryption", ["none", "external", "managed"])
def test_step_functions_sqs_validates(tmp_path, encryption):
    payload = architecture()
    if encryption == "managed":
        add_key(payload)
    elif encryption == "external":
        payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external-key"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
