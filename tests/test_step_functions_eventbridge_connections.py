"""Step Functions EventBridge connections publish events to scoped buses."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_eventbridge import eventbridge_workflow_locals
from app.models.connection_configs.step_functions_eventbridge import (
    StepFunctionsEventBridgeConfig,
)
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
from tests.test_step_functions_dynamodb_connections import (
    architecture as dynamodb_architecture,
)


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.EVENTBRIDGE, None, {})
    )


@pytest.mark.parametrize("custom_bus", [False, True])
def test_put_events_task_and_scoped_policy_generated(custom_bus):
    payload = architecture()
    if custom_bus:
        payload["resources"][1]["config"]["bus_name"] = "workflow-events"
    else:
        payload["resources"][1]["config"].pop("bus_name", None)
    tree = generate(payload)
    machine = next(v for p, v in tree.items() if p.endswith("/step-functions.tf"))
    task = next(v for p, v in tree.items() if p.endswith("/eventbridge_tasks.tf"))
    policy = next(
        v for p, v in tree.items() if p.endswith("/eventbridge_tasks_policy.tf")
    )
    bus = next(v for p, v in tree.items() if p.endswith("/eventbridge.tf"))
    assert "definition = local.eventbridge_workflow_definition" in machine
    assert "local.eventbridge_tasks_valid" in machine
    assert "states:::events:putEvents" in task
    assert '"Detail.$" = "States.JsonToString($)"' in task
    assert 'Source = "iaccreator.workflow"' in task
    assert 'DetailType = "Workflow Event"' in task
    assert "var.workflow_eventbridge_bus_0_arn" in task
    assert "events:PutEvents" in policy
    assert "var.workflow_eventbridge_bus_0_arn" in policy
    assert "module.target-resource.event_bus_arn" in "\n".join(tree.values())
    if custom_bus:
        assert 'resource "aws_cloudwatch_event_bus" "target-resource_bus"' in bus
    else:
        assert 'data "aws_cloudwatch_event_bus" "default"' in bus
    assert generate(payload) == tree


def test_constant_detail_and_multiple_buses_are_deterministic():
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
        "detail_json": '{"order":1}',
    }
    bus = deepcopy(payload["resources"][1])
    bus.update(id="second", name="second-bus")
    bus["config"]["bus_name"] = "second-events"
    payload["resources"].append(bus)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="second-bus", target_id="second")
    connection["connection_config"] = {"state_name": "Second"}
    payload["connections"].append(connection)
    tree = generate(payload)
    task = next(v for p, v in tree.items() if p.endswith("/eventbridge_tasks.tf"))
    policy = next(
        v for p, v in tree.items() if p.endswith("/eventbridge_tasks_policy.tf")
    )
    assert 'Detail = "{\\"order\\":1}"' in task
    assert "workflow_eventbridge_bus_0_arn" in policy
    assert "workflow_eventbridge_bus_1_arn" in policy
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "settings",
    [
        {"source": "aws.internal"},
        {"source": ""},
        {"source": " "},
        {"source": "a" * 257},
        {"detail_type": ""},
        {"detail_type": " "},
        {"detail_type": "a" * 129},
        {"detail_json": "not JSON"},
        {"detail_json": "[1]"},
    ],
)
def test_invalid_event_settings_rejected(settings):
    with pytest.raises(ValidationError):
        StepFunctionsEventBridgeConfig.model_validate(settings)


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
    duplicate["connection_config"] = {"detail_type": "Different"}
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_dynamodb_and_eventbridge_states_compose_in_any_order():
    payload = dynamodb_architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Lookup",
            "States": {
                "Lookup": {"Type": "Pass", "Next": "Publish"},
                "Publish": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"] = {"state_name": "Lookup"}
    bus = deepcopy(architecture()["resources"][1])
    bus.update(id="bus", name="events")
    payload["resources"].append(bus)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="events", target_id="bus")
    connection["connection_config"] = {"state_name": "Publish"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(v for p, v in tree.items() if p.endswith("/step-functions.tf"))
    task = next(v for p, v in tree.items() if p.endswith("/eventbridge_tasks.tf"))
    assert "local.dynamodb_workflow_definition" in task
    assert "local.dynamodb_tasks_valid" in machine
    assert "local.eventbridge_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_dynamodb_and_eventbridge_cannot_replace_the_same_state():
    payload = dynamodb_architecture()
    bus = deepcopy(architecture()["resources"][1])
    bus.update(id="bus", name="events")
    payload["resources"].append(bus)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="events", target_id="bus")
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="multiple task connections"):
        generate(payload)


def test_eventbridge_task_preserves_transition_and_data_path(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Publish",
        "States": {
            "Publish": {
                "Type": "Pass",
                "Next": "Done",
                "ResultPath": "$.event",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    content += (
        eventbridge_workflow_locals(
            {
                "Publish": {
                    "Entries": [
                        {
                            "EventBusName": Expr(
                                '"arn:aws:events:us-east-1:123456789012:event-bus/default"'
                            ),
                            "Source": "iaccreator.workflow",
                            "DetailType": "Workflow Event",
                            "Detail.$": "States.JsonToString($)",
                        }
                    ]
                }
            },
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        )
        .replace('data "aws_partition" "eventbridge_tasks" {}\n', "")
        .replace("data.aws_partition.eventbridge_tasks.partition", '"aws"')
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.eventbridge_tasks_valid, workflow = jsondecode(local.eventbridge_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    state = output["workflow"]["States"]["Publish"]
    assert state["Resource"] == "arn:aws:states:::events:putEvents"
    assert state["Next"] == "Done"
    assert state["ResultPath"] == "$.event"
    assert "Result" not in state
    assert state["Parameters"]["Entries"][0]["Detail.$"] == "States.JsonToString($)"


@needs_terraform
@pytest.mark.parametrize("custom_bus", [False, True])
def test_step_functions_eventbridge_validates(tmp_path, custom_bus):
    payload = architecture()
    if custom_bus:
        payload["resources"][1]["config"]["bus_name"] = "workflow-events"
    else:
        payload["resources"][1]["config"].pop("bus_name", None)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
