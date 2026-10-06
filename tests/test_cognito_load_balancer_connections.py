"""Cognito browser authentication composes with HTTPS forwarding listeners."""

from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.cognito_load_balancer import (
    CognitoLoadBalancerConfig,
)
from app.models.input_models import ServiceType
from app.models.input_models.cognito_config import CognitoConfig
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.COGNITO, ServiceType.LOAD_BALANCER, None, {})
    )


def confidential_clients(tree):
    return [
        item
        for item in resources(tree, "aws_cognito_user_pool_client")
        if item["generate_secret"]
    ]


def test_authentication_precedes_forwarding_with_native_references():
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        scopes="profile openid email email", session_timeout=1234
    )
    tree = generate(payload)
    actions = resources(tree, "aws_lb_listener")[0]["default_action"]
    assert [(item["type"], item["order"]) for item in actions] == [
        ("authenticate-cognito", 1),
        ("forward", 2),
    ]
    auth = actions[0]["authenticate_cognito"][0]
    assert auth["user_pool_arn"] == "${var.cognito_source-resource_user_pool_arn}"
    assert (
        auth["user_pool_client_id"]
        == "${aws_cognito_user_pool_client.cognito_source-resource_443_client.id}"
    )
    assert auth["user_pool_domain"] == "${var.cognito_source-resource_user_pool_domain}"
    assert auth["scope"] == "email openid profile"
    assert auth["session_timeout"] == 1234
    assert auth["on_unauthenticated_request"] == "authenticate"
    assert actions[1]["target_group_arn"] == "${var.app_group_target_group_arn}"
    client = confidential_clients(tree)[0]
    assert client["user_pool_id"] == "${var.cognito_source-resource_user_pool_id}"
    assert client["allowed_oauth_flows_user_pool_client"] is True
    assert client["allowed_oauth_flows"] == ["code"]
    assert client["allowed_oauth_scopes"] == ["email", "openid", "profile"]
    assert client["callback_urls"] == ["https://app.example.com/oauth2/idpresponse"]
    assert client["supported_identity_providers"] == ["COGNITO"]
    public = [
        item
        for item in resources(tree, "aws_cognito_user_pool_client")
        if not item["generate_secret"]
    ]
    assert len(public) == 1
    domain = resources(tree, "aws_cognito_user_pool_domain")[0]
    assert domain["domain"] == "${var.domain_prefix}"
    assert domain["user_pool_id"] == "${aws_cognito_user_pool.source-resource.id}"
    main = tree["connection-check/environments/dev/main.tf"]
    assert "module.source-resource.user_pool_domain" in main
    assert "module.source-resource.user_pool_arn" in main
    assert "module.source-resource.user_pool_id" in main
    assert "module.target-resource" not in file_with(
        tree, "/cognito/source-resource/cognito.tf"
    )
    assert "client_secret" not in "\n".join(tree.values())
    assert not ConnectionProcessor().process_all(project(payload)).iam
    assert generate(payload) == tree


@pytest.mark.parametrize("create_client", [False, True])
def test_alb_client_is_independent_of_public_client(create_client):
    payload = architecture()
    payload["resources"][0]["config"]["create_client"] = create_client
    tree = generate(payload)
    assert len(confidential_clients(tree)) == 1
    assert len(resources(tree, "aws_cognito_user_pool_client")) == 1 + create_client


def test_unconnected_pool_and_listener_do_not_gain_authentication():
    payload = architecture()
    payload["connections"].pop(0)
    payload["resources"][0]["config"].pop("domain_prefix")
    tree = generate(payload)
    assert not confidential_clients(tree)
    assert not resources(tree, "aws_cognito_user_pool_domain")
    assert (
        "authenticate_cognito"
        not in resources(tree, "aws_lb_listener")[0]["default_action"][0]
    )
    assert "domain_prefix" not in file_with(
        tree, "/cognito/source-resource/variables.tf"
    )


@settings(max_examples=12)
@given(
    order=st.permutations(range(3)),
    duplicates=st.integers(min_value=1, max_value=3),
    pool_name=resource_name_st,
)
def test_order_and_duplicate_connections_preserve_generated_tree(
    order, duplicates, pool_name
):
    payload = architecture()
    payload["resources"][0]["name"] = pool_name
    payload["connections"][0]["source"] = pool_name
    expected = generate(payload)
    payload["connections"] = [
        payload["connections"][index] for index in order
    ] * duplicates
    assert generate(payload) == expected
    assert len(confidential_clients(expected)) == 1


def add_listener(payload, port=8443, name="other-group"):
    group = deepcopy(payload["resources"][2])
    group.update(id=name, name=name)
    payload["resources"].append(group)
    listener = deepcopy(payload["connections"][1])
    listener.update(target=name, target_id=name)
    listener["connection_config"]["port"] = port
    payload["connections"].append(listener)


def test_selected_listener_is_protected_and_sessions_are_isolated():
    payload = architecture()
    add_listener(payload)
    tree = generate(payload)
    listeners = {item["port"]: item for item in resources(tree, "aws_lb_listener")}
    assert listeners[8443]["default_action"][0]["type"] == "forward"
    auth = deepcopy(payload["connections"][0])
    auth["connection_config"].update(
        listener_port=8443, application_hostname="Other.Example.COM"
    )
    payload["connections"].append(auth)
    tree = generate(payload)
    assert len(confidential_clients(tree)) == 2
    assert {item["callback_urls"][0] for item in confidential_clients(tree)} == {
        "https://app.example.com/oauth2/idpresponse",
        "https://other.example.com:8443/oauth2/idpresponse",
    }
    cookies = {
        item["default_action"][0]["authenticate_cognito"][0]["session_cookie_name"]
        for item in resources(tree, "aws_lb_listener")
    }
    assert len(cookies) == 2
    variables = file_with(tree, "/load-balancer/target-resource/variables.tf")
    assert variables.count('variable "cognito_source-resource_user_pool_id"') == 1
    expected = tree
    payload["connections"].reverse()
    assert generate(payload) == expected


@pytest.mark.parametrize(
    "setting,value",
    [
        ("scopes", "openid email"),
        ("session_timeout", 42),
        ("application_hostname", "other.example.com"),
        ("on_unauthenticated_request", "deny"),
    ],
)
def test_conflicting_settings_are_rejected_regardless_of_order(setting, value):
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"][setting] = value
    payload["connections"].append(other)
    for connections in (payload["connections"], list(reversed(payload["connections"]))):
        payload["connections"] = connections
        with pytest.raises(InvalidConnectionConfigError, match="only one Cognito pool"):
            generate(payload)


def test_multiple_pools_on_one_listener_are_rejected():
    payload = architecture()
    pool = deepcopy(payload["resources"][0])
    pool.update(name="other-pool", id="other")
    pool["config"]["domain_prefix"] = "other-login"
    payload["resources"].append(pool)
    auth = deepcopy(payload["connections"][0])
    auth.update(source="other-pool", source_id="other")
    payload["connections"].append(auth)
    with pytest.raises(InvalidConnectionConfigError, match="only one Cognito pool"):
        generate(payload)


def test_distinct_pools_on_separate_listeners_preserve_identifiers():
    payload = architecture()
    add_listener(payload)
    pool = deepcopy(payload["resources"][0])
    pool.update(name="source_resource", id="other-pool")
    pool["config"]["domain_prefix"] = "other-pool-login"
    payload["resources"].append(pool)
    auth = deepcopy(payload["connections"][0])
    auth.update(source="source_resource", source_id="other-pool")
    auth["connection_config"]["listener_port"] = 8443
    payload["connections"].append(auth)
    tree = generate(payload)
    assert len(confidential_clients(tree)) == 2
    assert {item["user_pool_id"] for item in confidential_clients(tree)} == {
        "${var.cognito_source-resource_user_pool_id}",
        "${var.cognito_source_resource_user_pool_id}",
    }
    expected = tree
    payload["connections"].reverse()
    assert generate(payload) == expected


def test_colliding_target_group_listener_names_are_rejected():
    payload = architecture()
    add_listener(payload, name="app_group")
    with pytest.raises(InvalidConnectionConfigError, match="names collide"):
        generate(payload)


@pytest.mark.parametrize(
    "failure",
    [
        "network",
        "domain",
        "http",
        "tls",
        "missing-listener",
        "missing-certificate",
        "ambiguous",
        "target-protocol",
        "same-target",
    ],
)
def test_invalid_listener_binding_is_rejected_before_generation_and_preview(failure):
    payload = architecture()
    if failure == "network":
        payload["resources"][1]["config"]["load_balancer_type"] = "network"
    elif failure == "domain":
        payload["resources"][0]["config"].pop("domain_prefix")
    elif failure in {"http", "tls"}:
        payload["connections"][1]["connection_config"]["protocol"] = failure.upper()
    elif failure == "missing-listener":
        payload["connections"].pop(1)
    elif failure == "missing-certificate":
        payload["connections"].pop(2)
    elif failure == "ambiguous":
        add_listener(payload, 443)
    elif failure == "target-protocol":
        payload["resources"][2]["config"]["protocol"] = "TCP"
    else:
        listener = deepcopy(payload["connections"][1])
        listener["connection_config"]["port"] = 8443
        payload["connections"].append(listener)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("explicit_target", [False, True])
def test_cross_region_client_creation_is_rejected(explicit_target):
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    if explicit_target:
        payload["resources"][1]["provider_region"] = "us-east-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_environment_region_override_keeps_alb_client_with_pool():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"] = {"region": "us-west-2"}
    tree = generate(payload)
    assert (
        'region = "us-west-2"' in tree["connection-check/environments/dev/provider.tf"]
    )
    client = confidential_clients(tree)[0]
    condition = client["lifecycle"][0]["precondition"][0]["condition"]
    assert "var.cognito_source-resource_user_pool_arn" in condition
    assert "aws_lb.target-resource.arn" in condition


@pytest.mark.parametrize("mode", ["authenticate", "deny", "allow"])
def test_preview_reports_requirements_and_optional_authentication(mode):
    payload = architecture()
    payload["connections"][0]["connection_config"]["on_unauthenticated_request"] = mode
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert [item.resource_type for item in preview.resources] == [
        "aws_cognito_user_pool_client"
    ]
    assert not preview.iam
    messages = " ".join(item.message for item in preview.issues)
    assert "IPv4" in messages and "DescribeUserPoolClient" in messages
    assert ("Unauthenticated requests" in messages) == (mode == "allow")
    auth = resources(generate(payload), "aws_lb_listener")[0]["default_action"][0][
        "authenticate_cognito"
    ][0]
    assert auth["on_unauthenticated_request"] == mode


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"application_hostname": "https://app.example.com"},
        {"application_hostname": "app.example.com:443"},
        {"application_hostname": "127.0.0.1"},
        {"application_hostname": "a..example.com"},
        {"application_hostname": "app.example.com/${bad}"},
        {"scopes": "email"},
        {"scopes": "openid app/read"},
        {"scopes": "openid,email"},
        {"session_timeout": 0},
        {"session_timeout": 604801},
        {"session_timeout": True},
        {"listener_port": 65536},
        {"listener_port": "443"},
        {"on_unauthenticated_request": "redirect"},
        {"unknown": "x"},
    ],
)
def test_invalid_connection_settings(config):
    value = (
        {} if config == {} else {"application_hostname": "app.example.com", **config}
    )
    with pytest.raises(ValidationError):
        CognitoLoadBalancerConfig.model_validate(value)


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "UPPER",
        "-login",
        "login-",
        "a" * 64,
        "aws-login",
        "my-amazon-login",
        "my-cognito-login",
        "https://login",
    ],
)
def test_invalid_domain_prefix(prefix):
    with pytest.raises(ValidationError):
        CognitoConfig(domain_prefix=prefix)


@needs_terraform
@pytest.mark.parametrize("two_listeners", [False, True])
def test_cognito_load_balancer_project_validates_without_cycles(
    tmp_path, two_listeners
):
    payload = architecture()
    payload["resources"][0]["config"]["create_client"] = False
    if two_listeners:
        add_listener(payload)
        auth = deepcopy(payload["connections"][0])
        auth["connection_config"]["listener_port"] = 8443
        payload["connections"].append(auth)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
