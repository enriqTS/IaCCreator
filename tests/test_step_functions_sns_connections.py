"""Step Functions SNS connections publish state input to generated topics."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_sns import sns_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsSnsConfig
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
from tests.test_step_functions_batch_connections import (
    architecture as batch_architecture,
)


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.SNS, None, {})
    )


def test_publish_task_and_topic_scoped_policy_generated():
    tree = generate(architecture())
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(value for path, value in tree.items() if path.endswith("/sns_tasks.tf"))
    policy = next(
        value for path, value in tree.items() if path.endswith("/sns_tasks_policy.tf")
    )
    assert "definition = local.sns_workflow_definition" in machine
    assert "local.sns_tasks_valid" in machine
    assert "sns:publish" in task
    assert '"Message.$" = "States.JsonToString($)"' in task
    assert "var.workflow_sns_topic_0_arn" in task
    assert "sns:Publish" in policy
    assert "Resource = [" in policy and "var.workflow_sns_topic_0_arn" in policy
    assert "kms:Decrypt" not in policy
    assert "module.target-resource.topic_arn" in "\n".join(tree.values())
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
    task = next(value for path, value in tree.items() if path.endswith("/sns_tasks.tf"))
    assert 'Message = "ready"' in task
    assert '"Message.$" = "States.JsonToString($)"' in task
    assert sum(path.endswith("/sns_tasks_policy.tf") for path in tree) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_fifo_topic_requires_group_and_generates_deduplication_id():
    payload = architecture()
    payload["resources"][1]["config"]["fifo_topic"] = True
    with pytest.raises(InvalidConnectionConfigError, match="must end in .fifo"):
        generate(payload)
    payload["resources"][1]["config"].update(
        fifo_topic=True, topic_name="messages.fifo"
    )
    with pytest.raises(InvalidConnectionConfigError, match="message group ID"):
        generate(payload)
    payload["connections"][0]["connection_config"] = {"message_group_id": "orders"}
    tree = generate(payload)
    task = next(value for path, value in tree.items() if path.endswith("/sns_tasks.tf"))
    assert 'MessageGroupId = "orders"' in task
    assert '"MessageDeduplicationId.$" = "States.UUID()"' in task
    payload["resources"][1]["config"]["content_based_deduplication"] = True
    task = next(
        value
        for path, value in generate(payload).items()
        if path.endswith("/sns_tasks.tf")
    )
    assert "MessageDeduplicationId" not in task


def test_standard_topic_rejects_fifo_settings_and_empty_message():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"message_group_id": "orders"}
    with pytest.raises(InvalidConnectionConfigError, match="require a FIFO topic"):
        generate(payload)
    payload["connections"][0]["connection_config"] = {"message": ""}
    with pytest.raises(InvalidConnectionConfigError, match="must contain"):
        generate(payload)


def test_missing_role_or_invalid_placeholder_rejected():
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


def test_invalid_group_id_and_conflicting_state_rejected():
    with pytest.raises(ValidationError):
        StepFunctionsSnsConfig(message_group_id="bad group")
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"] = {"message": "different"}
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_sns_and_batch_cannot_replace_the_same_state():
    payload = batch_architecture()
    sns = deepcopy(architecture()["resources"][1])
    sns.update(id="topic", name="alerts")
    payload["resources"].append(sns)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource",
        source_id="src",
        target="alerts",
        target_id="topic",
    )
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="multiple task connections"):
        generate(payload)


@pytest.mark.parametrize("managed", [False, True])
def test_encrypted_topics_grant_scoped_kms_access(managed):
    payload = architecture()
    if managed:
        add_key(payload)
    else:
        payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external-key"
    tree = generate(payload)
    policy = next(
        value for path, value in tree.items() if path.endswith("/sns_tasks_policy.tf")
    )
    assert "kms:Decrypt" in policy and "kms:GenerateDataKey*" in policy
    if managed:
        assert "var.workflow_sns_key_0_arn" in policy
        assert "module.encryption-key.key_arn" in "\n".join(tree.values())
    else:
        assert "data.aws_kms_key.workflow_sns_key_0_arn.arn" in policy
        assert "module.target-resource.kms_access_key_id" in "\n".join(tree.values())


def test_batch_and_sns_states_compose_in_any_order():
    payload = batch_architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Job",
            "States": {
                "Job": {"Type": "Pass", "Next": "Notify"},
                "Notify": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"]["state_name"] = "Job"
    sns = deepcopy(architecture()["resources"][1])
    sns.update(id="topic", name="alerts")
    payload["resources"].append(sns)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource", source_id="src", target="alerts", target_id="topic"
    )
    connection["connection_config"] = {"state_name": "Notify"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(value for path, value in tree.items() if path.endswith("/sns_tasks.tf"))
    assert "local.batch_workflow_definition" in task
    assert "local.batch_tasks_valid" in machine
    assert "local.sns_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_sns_task_preserves_transition_and_data_path(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Notify",
        "States": {
            "Notify": {
                "Type": "Pass",
                "Next": "Done",
                "ResultPath": "$.published",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    content += (
        sns_workflow_locals(
            {
                "Notify": {
                    "TopicArn": Expr('"topic-arn"'),
                    "Message.$": "States.JsonToString($)",
                }
            },
            False,
            False,
            False,
            False,
        )
        .replace('data "aws_partition" "sns_tasks" {}\n', "")
        .replace("data.aws_partition.sns_tasks.partition", '"aws"')
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.sns_tasks_valid, workflow = jsondecode(local.sns_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    state = output["workflow"]["States"]["Notify"]
    assert state["Resource"] == "arn:aws:states:::sns:publish"
    assert state["Next"] == "Done"
    assert state["ResultPath"] == "$.published"
    assert "Result" not in state
    assert state["Parameters"]["Message.$"] == "States.JsonToString($)"


@needs_terraform
@pytest.mark.parametrize("encryption", ["none", "external", "managed"])
def test_step_functions_sns_validates(tmp_path, encryption):
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
