"""Workflow targets use rule-owned roles and native state-machine references."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.eventbridge_workflow import EventBridgeWorkflowConfig
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


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.STEP_FUNCTIONS, None, {})
    )


@given(
    target_id=st.from_regex(r"[A-Za-z][A-Za-z0-9_-]{0,20}", fullmatch=True),
    constant=st.sampled_from([None, '{"job":"daily"}', "[]"]),
)
def test_scoped_role_and_input(target_id, constant):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "target_id": target_id,
        "input": constant,
    }
    tree = generate(payload)
    resource = next(v for k, v in tree.items() if "/workflow_" in k)
    assert f'target_id = "{target_id}"' in resource
    assert '"states:StartExecution"' in resource
    assert "StartSyncExecution" not in resource
    assert "events.amazonaws.com" in resource
    assert "aws:SourceArn" in resource
    assert "aws_cloudwatch_event_rule.source-resource.arn" in resource
    assert "depends_on = [aws_iam_role_policy.workflow_" in resource
    assert ("input =" in resource) == (constant is not None)
    assert "module.target-resource.state_machine_arn" in "\n".join(tree.values())
    target_files = "\n".join(v for k, v in tree.items() if "/target-resource/" in k)
    assert "aws_cloudwatch_event_target" not in target_files
    assert "module.source-resource" not in target_files
    payload["connections"] *= 2
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "value", ["oops", "{", "NaN", "Infinity", '"' + "a" * 8192 + '"']
)
def test_invalid_constant_input_rejected(value):
    with pytest.raises(ValidationError):
        EventBridgeWorkflowConfig(input=value)


def test_conflicting_target_input_rejected():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"target_id": "job"}
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["input"] = "{}"
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError, match="uniquely"):
        generate(payload)


def test_multiple_target_ids_to_same_workflow_are_preserved():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"target_id": "first"}
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {"target_id": "second", "input": "{}"}
    payload["connections"].append(other)
    tree = generate(payload)
    assert (
        sum('resource "aws_cloudwatch_event_target"' in v for v in tree.values()) == 2
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.parametrize("workflow_type", ["STANDARD", "EXPRESS"])
def test_workflow_target_validates(workflow_type, tmp_path):
    payload = architecture()
    payload["resources"][1]["config"]["state_machine_type"] = workflow_type
    payload["connections"][0]["connection_config"]["input"] = '{"job":"daily"}'
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
