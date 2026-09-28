"""HTTP API POST routes start generated Step Functions workflows."""

from copy import deepcopy

import pytest

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
        resolve_spec(ServiceType.API_GATEWAY, ServiceType.STEP_FUNCTIONS, None, {})
    )


def test_post_route_starts_workflow_with_scoped_role():
    tree = generate(architecture())
    gateway = next(
        value
        for path, value in tree.items()
        if path.endswith("/workflow_target-resource.tf")
    )
    generated = "\n".join(tree.values())
    assert 'integration_subtype = "StepFunctions-StartExecution"' in gateway
    assert "StateMachineArn" in gateway
    assert '"$request.body"' in gateway
    assert '"states:StartExecution"' in gateway
    assert '"apigateway.amazonaws.com"' in gateway
    assert 'route_key = "POST /start"' in gateway
    assert 'authorization_type = "AWS_IAM"' in gateway
    assert "module.target-resource.state_machine_arn" in generated
    assert generated.count('route_key = "POST /start"') == 1
    assert generate(architecture()) == tree


def test_missing_route_rejected():
    payload = architecture()
    payload["resources"][0]["config"].pop("routes")
    with pytest.raises(Exception, match="Bind at least one POST route"):
        generate(payload)


def test_non_post_route_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["routes"][0]["methods"] = ["GET"]
    with pytest.raises(Exception, match="POST only"):
        generate(payload)


def test_websocket_api_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["protocol_type"] = "WEBSOCKET"
    with pytest.raises(Exception, match="HTTP API"):
        generate(payload)


def test_conflicting_route_authorizer_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["routes"][0]["authorization_type"] = "NONE"
    with pytest.raises(Exception, match="AWS_IAM authorization"):
        generate(payload)


def test_gateway_api_key_requirement_is_preserved():
    payload = architecture()
    payload["resources"][0]["config"]["api_key_required"] = True
    tree = generate(payload)
    gateway = next(
        value
        for path, value in tree.items()
        if path.endswith("/workflow_target-resource.tf")
    )
    assert "api_key_required = true" in gateway


def test_multiple_workflows_keep_distinct_routes():
    payload = architecture()
    workflow = deepcopy(payload["resources"][1])
    workflow.update(id="next", name="next-workflow")
    payload["resources"].append(workflow)
    payload["resources"][0]["config"]["routes"].append(
        {
            "path": "/next",
            "methods": ["POST"],
            "integration_name": "next-workflow",
            "integration_id": "next",
        }
    )
    connection = deepcopy(payload["connections"][0])
    connection.update(target="next-workflow", target_id="next")
    payload["connections"].append(connection)
    tree = generate(payload)
    generated = "\n".join(tree.values())
    assert generated.count('route_key = "POST /start"') == 1
    assert generated.count('route_key = "POST /next"') == 1


@needs_terraform
def test_apigw_step_functions_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
