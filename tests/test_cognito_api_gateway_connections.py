"""Cognito JWT authorizers bind existing HTTP routes and compose with integrations."""

from copy import deepcopy

import hcl2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.cognito_api_gateway import CognitoApiGatewayConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder
from tests.conftest import resource_name_st
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
        resolve_spec(ServiceType.COGNITO, ServiceType.API_GATEWAY, None, {})
    )


def file_with(tree, suffix):
    return next(value for path, value in tree.items() if path.endswith(suffix))


def resources(tree, resource_type):
    result = []
    for content in tree.values():
        if f'resource "{resource_type}"' not in content:
            continue
        parsed = hcl2.loads(
            content,
            serialization_options=hcl2.utils.SerializationOptions(
                strip_string_quotes=True
            ),
        )
        for resource in parsed.get("resource", []):
            result.extend(resource.get(resource_type, {}).values())
    return result


def route(tree, key):
    return next(
        item
        for item in resources(tree, "aws_apigatewayv2_route")
        if item["route_key"] == key
    )


def bind_lambda(payload):
    lambda_payload = connection_architecture(
        resolve_spec(ServiceType.API_GATEWAY, ServiceType.LAMBDA, None, {})
    )
    function = lambda_payload["resources"][1]
    function.update(id="function", name="function")
    payload["resources"].append(function)
    payload["resources"][1]["config"]["routes"][0].update(
        integration_name="function", integration_id="function"
    )
    connection = lambda_payload["connections"][0]
    connection.update(
        source="target-resource",
        source_id="tgt",
        target="function",
        target_id="function",
    )
    connection["connection_config"].pop("routes", None)
    payload["connections"].append(connection)


def test_generated_authorizer_references_native_pool_endpoint_and_client():
    payload = architecture()
    payload["connections"][0]["connection_config"]["authorization_scopes"] = (
        "catalog/read"
    )
    tree = generate(payload)
    authorizer = resources(tree, "aws_apigatewayv2_authorizer")[0]
    assert authorizer["authorizer_type"] == "JWT"
    assert authorizer["identity_sources"] == ["$request.header.Authorization"]
    assert authorizer["jwt_configuration"][0]["audience"] == [
        "${var.cognito_source-resource_client_id}"
    ]
    content = file_with(tree, "/cognito_authorizer_source-resource.tf")
    assert (
        'issuer = format("https://%s", var.cognito_source-resource_endpoint)' in content
    )
    main = tree["connection-check/environments/dev/main.tf"]
    assert "module.source-resource.endpoint" in main
    assert "module.source-resource.client_id" in main
    protected = route(tree, "GET /private")
    assert protected["authorization_type"] == "JWT"
    assert (
        protected["authorizer_id"]
        == "${aws_apigatewayv2_authorizer.cognito_source-resource_jwt.id}"
    )
    assert protected["authorization_scopes"] == ["catalog/read"]
    assert "authorizer_uri" not in content
    assert "authorizer_credentials_arn" not in content
    assert "aws_lambda_permission" not in content
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    assert not ConnectionProcessor().process_all(project).iam
    assert generate(payload) == tree


@pytest.mark.parametrize("bound_lambda", [False, True])
def test_only_selected_method_is_protected(bound_lambda):
    payload = architecture()
    payload["resources"][1]["config"]["routes"][0]["methods"] = ["GET", "POST"]
    if bound_lambda:
        bind_lambda(payload)
    tree = generate(payload)
    assert route(tree, "GET /private")["authorization_type"] == "JWT"
    assert route(tree, "POST /private").get("authorization_type") != "JWT"
    assert len(resources(tree, "aws_apigatewayv2_route")) == 2
    if bound_lambda:
        assert (
            "aws_apigatewayv2_integration.function_integration.id"
            in route(tree, "GET /private")["target"]
        )
    payload["connections"].reverse()
    assert generate(payload) == tree


@given(names=st.lists(resource_name_st, min_size=1, max_size=4, unique=True))
@settings(max_examples=20)
def test_multiple_routes_share_authorizer_with_deterministic_duplicate_connections(
    names,
):
    payload = architecture()
    payload["resources"][1]["config"]["routes"] = [
        {"path": f"/{name}", "methods": ["GET"]} for name in names
    ]
    template = payload["connections"][0]
    payload["connections"] = [
        {
            **deepcopy(template),
            "connection_config": {
                "path": f"/{name}",
                "method": "GET",
                "authorization_scopes": "write,read,read",
            },
        }
        for name in names
    ]
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_authorizer")) == 1
    for name in names:
        assert route(tree, f"GET /{name}")["authorization_scopes"] == ["read", "write"]
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(payload["connections"][0]))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "inherited,override,expected",
    [
        (["route/read"], None, ["route/read"]),
        (["route/read"], "custom/write,custom/read", ["custom/read", "custom/write"]),
        (["route/read"], "", []),
    ],
)
def test_route_scopes_are_inherited_or_explicitly_overridden(
    inherited, override, expected
):
    payload = architecture()
    bind_lambda(payload)
    payload["resources"][1]["config"]["routes"][0]["authorization_scopes"] = inherited
    payload["connections"][0]["connection_config"]["authorization_scopes"] = override
    assert route(generate(payload), "GET /private")["authorization_scopes"] == expected


def test_top_level_scopes_are_inherited():
    payload = architecture()
    payload["resources"][1]["config"]["authorization_scopes"] = ["api/read"]
    assert route(generate(payload), "GET /private")["authorization_scopes"] == [
        "api/read"
    ]


@pytest.mark.parametrize("method", ["GET", "get"])
def test_explicit_lambda_routes_are_protected_without_gateway_route_entries(method):
    payload = architecture()
    bind_lambda(payload)
    payload["resources"][1]["config"]["routes"] = []
    payload["connections"][1]["connection_config"]["routes"] = [
        {"path": "/private", "methods": [method]}
    ]
    assert route(generate(payload), "GET /private")["authorization_type"] == "JWT"


def test_conflicting_explicit_lambda_route_settings_rejected():
    payload = architecture()
    bind_lambda(payload)
    payload["connections"][1]["connection_config"]["routes"] = [
        {"path": "/private", "methods": ["GET"], "api_key_required": True}
    ]
    with pytest.raises(InvalidConnectionConfigError, match="API keys"):
        generate(payload)


def test_configured_http_proxy_integration_is_preserved():
    payload = architecture()
    payload["resources"][1]["config"]["integrations"] = [
        {
            "name": "backend",
            "type": "HTTP_PROXY",
            "uri": "https://example.com",
            "method": "GET",
        }
    ]
    payload["resources"][1]["config"]["routes"][0]["integration_name"] = "backend"
    protected = route(generate(payload), "GET /private")
    assert protected["authorization_type"] == "JWT"
    assert (
        "aws_apigatewayv2_integration.target-resource_backend_integration.id"
        in protected["target"]
    )


def test_distinct_pool_names_keep_distinct_authorizers_and_inputs():
    payload = architecture()
    pool = deepcopy(payload["resources"][0])
    pool.update(id="pool-two", name="source_resource")
    payload["resources"].append(pool)
    payload["resources"][1]["config"]["routes"].append(
        {"path": "/second", "methods": ["GET"]}
    )
    connection = deepcopy(payload["connections"][0])
    connection.update(source="source_resource", source_id="pool-two")
    connection["connection_config"]["path"] = "/second"
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_authorizer")) == 2
    main = tree["connection-check/environments/dev/main.tf"]
    assert "cognito_source-resource_client_id" in main
    assert "cognito_source_resource_client_id" in main
    payload["connections"][1]["connection_config"]["path"] = "/private"
    with pytest.raises(InvalidConnectionConfigError, match="only one Cognito pool"):
        generate(payload)


def test_conflicting_scopes_for_same_route_rejected():
    payload = architecture()
    second = deepcopy(payload["connections"][0])
    second["connection_config"]["authorization_scopes"] = "write"
    payload["connections"].append(second)
    with pytest.raises(InvalidConnectionConfigError, match="one scope configuration"):
        generate(payload)


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("protocol_type", "WEBSOCKET", "HTTP API"),
        ("body", '{"openapi":"3.0.1"}', "OpenAPI body"),
        ("authorization_type", "AWS_IAM", "IAM authorization"),
        ("authorization_type", "CUSTOM", "another authorizer"),
        ("api_key_required", True, "API keys"),
    ],
)
def test_unsupported_api_settings_rejected(field, value, message):
    payload = architecture()
    payload["resources"][1]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError, match=message):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("authorizer_name", "existing"),
        ("authorization_type", "AWS_IAM"),
        ("api_key_required", True),
    ],
)
def test_conflicting_route_settings_rejected(field, value):
    payload = architecture()
    payload["resources"][1]["config"]["routes"][0][field] = value
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_disabled_client_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["create_client"] = False
    with pytest.raises(
        InvalidConnectionConfigError, match="generated application client"
    ):
        generate(payload)


@pytest.mark.parametrize(
    "method,path", [("POST", "/private"), ("GET", "/missing"), ("ANY", "/private")]
)
def test_route_selection_requires_exact_existing_method_and_path(method, path):
    payload = architecture()
    payload["connections"][0]["connection_config"].update(method=method, path=path)
    with pytest.raises(InvalidConnectionConfigError, match="exact configured method"):
        generate(payload)


def test_missing_managed_integration_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["routes"][0]["integration_name"] = "missing"
    with pytest.raises(InvalidConnectionConfigError, match="no generated integration"):
        generate(payload)


def test_workflow_routes_reject_jwt_regardless_of_processing_order():
    payload = architecture()
    workflow_payload = connection_architecture(
        resolve_spec(ServiceType.API_GATEWAY, ServiceType.STEP_FUNCTIONS, None, {})
    )
    workflow = workflow_payload["resources"][1]
    workflow.update(id="workflow", name="workflow")
    payload["resources"].append(workflow)
    payload["resources"][1]["config"]["routes"][0].update(
        methods=["POST"], integration_name="workflow", integration_id="workflow"
    )
    payload["connections"][0]["connection_config"]["method"] = "POST"
    connection = workflow_payload["connections"][0]
    connection.update(
        source="target-resource",
        source_id="tgt",
        target="workflow",
        target_id="workflow",
    )
    connection["connection_config"].pop("routes", None)
    payload["connections"].append(connection)
    for _ in range(2):
        with pytest.raises(InvalidConnectionConfigError):
            generate(payload)
        payload["connections"].reverse()


def test_native_pool_endpoint_handles_cross_region_and_environment_override():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "us-west-2"
    payload["environments"][0]["variables"] = {"region": "eu-west-1"}
    tree = generate(payload)
    assert (
        "module.source-resource.endpoint"
        in tree["connection-check/environments/dev/main.tf"]
    )
    assert (
        'issuer = format("https://%s", var.cognito_source-resource_endpoint)'
        in file_with(tree, "/cognito_authorizer_source-resource.tf")
    )


@pytest.mark.parametrize("scopes,expected_warning", [(None, True), ("api/read", False)])
def test_preview_reports_authorizer_and_scope_guidance(scopes, expected_warning):
    payload = architecture()
    payload["connections"][0]["connection_config"]["authorization_scopes"] = scopes
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    preview = ConnectionPreviewer().preview_all(project)[0]
    assert preview.resources[0].resource_type == "aws_apigatewayv2_authorizer"
    assert not preview.iam
    assert (
        any("ID tokens" in issue.message for issue in preview.issues)
        == expected_warning
    )


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"path": "private"},
        {"path": "/private", "method": "TRACE"},
        {"path": "/private", "authorization_scopes": "read,,write"},
        {"path": "/private", "authorization_scopes": "read write"},
        {"path": "/private", "authorization_scopes": "réad"},
        {"path": "/private", "client_id": "copied"},
    ],
)
def test_invalid_config_rejected(config):
    with pytest.raises(ValidationError):
        CognitoApiGatewayConfig.model_validate(config)


def test_any_method_route_is_supported():
    payload = architecture()
    payload["resources"][1]["config"]["routes"][0]["methods"] = ["ANY"]
    payload["connections"][0]["connection_config"]["method"] = "any"
    assert route(generate(payload), "ANY /private")["authorization_type"] == "JWT"


def test_unconnected_api_does_not_gain_authorizer():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    assert not resources(tree, "aws_apigatewayv2_authorizer")
    assert "authorizer_id" not in route(tree, "GET /private")


@needs_terraform
@pytest.mark.parametrize("bound_lambda", [False, True])
def test_cognito_api_gateway_project_validates(tmp_path, bound_lambda):
    payload = architecture()
    if bound_lambda:
        bind_lambda(payload)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
