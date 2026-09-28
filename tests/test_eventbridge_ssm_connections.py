"""EventBridge Run Command targets use a Command document and scoped instance."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models.connection_configs.eventbridge_ssm import EventBridgeSsmConfig
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
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.SYSTEMS_MANAGER, None, {})
    )


def test_target_scopes_document_and_instance():
    tree = generate(architecture())
    target = next(value for key, value in tree.items() if "/ssm_" in key)
    assert '"ssm:SendCommand"' in target
    assert "var.ssm_" in target
    assert "document_arn" in "\n".join(tree.values())
    assert '"i-0123456789abcdef0")' in target
    assert 'key = "InstanceIds"' in target
    assert 'values = ["i-0123456789abcdef0"]' in target
    assert 'document_type == "Command"' in target
    assert "events.amazonaws.com" in target
    assert generate(architecture()) == tree


def test_non_command_document_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["document_type"] = "Automation"
    with pytest.raises(Exception, match="Command document"):
        generate(payload)


def test_invalid_instance_id_rejected():
    with pytest.raises(ValidationError):
        EventBridgeSsmConfig(instance_id="*")


def test_distinct_targets_are_stable():
    payload = architecture()
    payload["connections"][0]["connection_config"]["target_id"] = "first"
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {
        "target_id": "second",
        "instance_id": "i-1234567890abcdef0",
    }
    payload["connections"].append(other)
    tree = generate(payload)
    assert (
        sum(
            'resource "aws_cloudwatch_event_target"' in value for value in tree.values()
        )
        == 2
    )
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@needs_terraform
def test_ssm_target_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
