"""EventBridge HTTP API targets use a deployed route and a scoped role."""

from copy import deepcopy

import pytest

from app.exceptions import InvalidConnectionConfigError
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
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.API_GATEWAY, None, {})
    )


def test_target_uses_route_arn_and_scoped_execution_role():
    tree = generate(architecture())
    target = next(v for k, v in tree.items() if "/api_" in k)
    assert '"execute-api:Invoke"' in target
    assert "/$default/POST/events" in target
    assert "role_arn = aws_iam_role.api_" in target
    assert "module.target-resource.target-resource_execution_arn" in "\n".join(
        tree.values()
    )
    assert generate(architecture()) == tree


@pytest.mark.parametrize(
    "change",
    [
        {"protocol_type": "WEBSOCKET"},
        {"disable_execute_api_endpoint": True},
        {"routes": []},
        {"stages": [{"name": "prod"}]},
    ],
)
def test_unsupported_gateway_rejected(change):
    payload = architecture()
    payload["resources"][1]["config"].update(change)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_route_requires_iam_authorization_and_integration():
    for field, value in [
        ("authorization_type", "NONE"),
        ("integration_name", "missing"),
        ("authorizer_name", "other"),
        ("api_key_required", True),
    ]:
        payload = architecture()
        payload["resources"][1]["config"]["routes"][0][field] = value
        with pytest.raises(InvalidConnectionConfigError):
            generate(payload)


def test_target_id_cannot_reuse_different_route_settings():
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["input"] = '{"different":true}'
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@needs_terraform
def test_api_target_terraform_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
