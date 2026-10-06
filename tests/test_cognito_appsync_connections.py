"""Cognito authentication owns AppSync providers without adding runtime IAM grants."""

from copy import deepcopy

import hcl2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.cognito_appsync import CognitoAppSyncConfig
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


def architecture(mode="default"):
    payload = connection_architecture(
        resolve_spec(ServiceType.COGNITO, ServiceType.APPSYNC, None, {})
    )
    payload["connections"][0]["connection_config"] = {"mode": mode}
    return payload


def file_with(tree, suffix):
    return next(content for path, content in tree.items() if path.endswith(suffix))


def api_attributes(tree):
    data = hcl2.loads(
        file_with(tree, "/appsync/target-resource/appsync.tf"),
        serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True),
    )
    return data["resource"][0]["aws_appsync_graphql_api"]["target-resource"]


def add_pool(payload, name, mode="additional"):
    pool = deepcopy(payload["resources"][0])
    pool.update(id=name, name=name)
    payload["resources"].append(pool)
    connection = deepcopy(payload["connections"][0])
    connection.update(source=name, source_id=name)
    connection["connection_config"] = {"mode": mode}
    payload["connections"].append(connection)


def test_default_provider_uses_native_pool_and_client_and_suppresses_api_key():
    payload = architecture()
    tree = generate(payload)
    api = api_attributes(tree)
    pool = api["user_pool_config"][0]
    assert api["authentication_type"] == "AMAZON_COGNITO_USER_POOLS"
    assert pool["default_action"] == "ALLOW"
    assert pool["user_pool_id"] == "${var.cognito_source-resource_user_pool_id}"
    assert pool["aws_region"] == "${var.cognito_source-resource_region}"
    assert (
        'app_id_client_regex = format("^%s$", var.cognito_source-resource_client_id)'
        in file_with(tree, "/appsync/target-resource/appsync.tf")
    )
    assert "aws_appsync_api_key" not in "\n".join(tree.values())
    assert "api_key_id" not in file_with(tree, "/appsync/target-resource/outputs.tf")
    main = tree["connection-check/environments/dev/main.tf"]
    assert "module.source-resource.user_pool_id" in main
    assert "module.source-resource.client_id" in main
    assert "module.source-resource.appsync_user_pool_region" in main
    outputs = file_with(tree, "/cognito/source-resource/outputs.tf")
    assert 'split(":", aws_cognito_user_pool.source-resource.arn)[3]' in outputs
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    contribution = ConnectionProcessor().process_all(project)
    assert not contribution.iam
    assert not contribution.resources
    assert generate(payload) == tree


@pytest.mark.parametrize("authentication_type", ["API_KEY", "AWS_IAM"])
def test_additional_provider_keeps_default_authentication(authentication_type):
    payload = architecture("additional")
    payload["resources"][1]["config"]["authentication_type"] = authentication_type
    tree = generate(payload)
    api = api_attributes(tree)
    assert api["authentication_type"] == "${var.authentication_type}"
    assert "user_pool_config" not in api
    provider = api["additional_authentication_provider"][0]
    assert provider["authentication_type"] == "AMAZON_COGNITO_USER_POOLS"
    assert "default_action" not in provider["user_pool_config"][0]
    assert ("aws_appsync_api_key" in "\n".join(tree.values())) == (
        authentication_type == "API_KEY"
    )


def test_client_filter_requires_generated_client_or_explicit_opt_out():
    payload = architecture()
    payload["resources"][0]["config"]["create_client"] = False
    with pytest.raises(InvalidConnectionConfigError, match="create_client"):
        generate(payload)
    payload["connections"][0]["connection_config"]["restrict_to_client"] = False
    tree = generate(payload)
    assert "app_id_client_regex" not in api_attributes(tree)["user_pool_config"][0]
    assert (
        "module.source-resource.client_id"
        not in tree["connection-check/environments/dev/main.tf"]
    )


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=4, unique=True).filter(
        lambda names: "source-resource" not in names
    )
)
@settings(max_examples=25)
def test_multiple_providers_are_deterministic_and_duplicate_connections_are_idempotent(
    names,
):
    payload = architecture()
    for name in names:
        add_pool(payload, name)
    tree = generate(payload)
    api = api_attributes(tree)
    assert len(api["additional_authentication_provider"]) == len(names)
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(payload["connections"][0]))
    assert generate(payload) == tree


def test_names_with_hyphen_and_underscore_use_distinct_inputs():
    payload = architecture("additional")
    add_pool(payload, "source_resource")
    tree = generate(payload)
    api = file_with(tree, "/appsync/target-resource/appsync.tf")
    assert "var.cognito_source-resource_user_pool_id" in api
    assert "var.cognito_source_resource_user_pool_id" in api
    assert len(api_attributes(tree)["additional_authentication_provider"]) == 2


@pytest.mark.parametrize("other_mode", ["default", "additional"])
def test_conflicting_configs_for_same_pool_rejected(other_mode):
    payload = architecture()
    second = deepcopy(payload["connections"][0])
    second["connection_config"] = {"mode": other_mode, "restrict_to_client": False}
    payload["connections"].append(second)
    with pytest.raises(
        InvalidConnectionConfigError, match="one authentication configuration"
    ):
        generate(payload)


def test_multiple_default_pools_rejected():
    payload = architecture()
    add_pool(payload, "second-pool", "default")
    with pytest.raises(InvalidConnectionConfigError, match="only one default"):
        generate(payload)


def test_default_deny_cannot_be_combined_with_additional_providers():
    payload = architecture()
    payload["connections"][0]["connection_config"]["default_action"] = "DENY"
    assert (
        api_attributes(generate(payload))["user_pool_config"][0]["default_action"]
        == "DENY"
    )
    add_pool(payload, "second-pool")
    with pytest.raises(InvalidConnectionConfigError, match="must be ALLOW"):
        generate(payload)


def test_same_pool_can_authenticate_multiple_apis_without_duplicate_outputs():
    payload = architecture()
    api = deepcopy(payload["resources"][1])
    api.update(id="second-api", name="second-api")
    payload["resources"].append(api)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="second-api", target_id="second-api")
    payload["connections"].append(connection)
    tree = generate(payload)
    assert (
        file_with(tree, "/cognito/source-resource/outputs.tf").count(
            'output "appsync_user_pool_region"'
        )
        == 1
    )
    assert "var.cognito_source-resource_user_pool_id" in file_with(
        tree, "/appsync/second-api/appsync.tf"
    )


def test_cross_region_uses_pool_native_region_even_with_environment_region_override():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "us-west-2"
    payload["environments"][0]["variables"] = {"region": "eu-west-1"}
    tree = generate(payload)
    assert (
        api_attributes(tree)["user_pool_config"][0]["aws_region"]
        == "${var.cognito_source-resource_region}"
    )
    assert 'split(":", aws_cognito_user_pool.source-resource.arn)[3]' in file_with(
        tree, "/cognito/source-resource/outputs.tf"
    )


@pytest.mark.parametrize(
    "mode,action,restricted,message",
    [
        ("additional", "ALLOW", True, "@aws_cognito_user_pools"),
        ("default", "DENY", True, "@aws_auth"),
        ("default", "ALLOW", False, "any application client"),
    ],
)
def test_preview_explains_required_authorization(mode, action, restricted, message):
    payload = architecture(mode)
    payload["connections"][0]["connection_config"].update(
        default_action=action, restrict_to_client=restricted
    )
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    preview = ConnectionPreviewer().preview_all(project)[0]
    assert any(message in issue.message for issue in preview.issues)
    assert not preview.iam


@pytest.mark.parametrize(
    "config",
    [
        {"mode": "unknown"},
        {"default_action": "UNKNOWN"},
        {"mode": "additional", "default_action": "DENY"},
        {"app_id_client_regex": ".*"},
    ],
)
def test_invalid_config_rejected(config):
    with pytest.raises(ValidationError):
        CognitoAppSyncConfig.model_validate(config)


def test_unconnected_api_retains_api_key():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    api = api_attributes(tree)
    assert api["authentication_type"] == "${var.authentication_type}"
    assert "user_pool_config" not in api
    assert "aws_appsync_api_key" in "\n".join(tree.values())
    assert "appsync_user_pool_region" not in "\n".join(tree.values())


def test_authentication_composes_with_lambda_resolver():
    payload = architecture()
    resolver_payload = connection_architecture(
        resolve_spec(ServiceType.APPSYNC, ServiceType.LAMBDA, None, {})
    )
    function = resolver_payload["resources"][1]
    function.update(id="function", name="function")
    payload["resources"].append(function)
    resolver = resolver_payload["connections"][0]
    resolver.update(
        source="target-resource",
        source_id="tgt",
        target="function",
        target_id="function",
    )
    payload["connections"].append(resolver)
    tree = generate(payload)
    assert api_attributes(tree)["authentication_type"] == "AMAZON_COGNITO_USER_POOLS"
    assert 'type = "AWS_LAMBDA"' in file_with(tree, "/lambda_datasource_function.tf")
    assert "aws_appsync_api_key" not in "\n".join(tree.values())


@needs_terraform
@pytest.mark.parametrize("mode", ["default", "additional", "multiple"])
def test_cognito_appsync_project_validates(tmp_path, mode):
    payload = architecture("additional" if mode == "additional" else "default")
    if mode == "multiple":
        add_pool(payload, "second-pool")
        add_pool(payload, "third-pool")
        payload["resources"][0]["provider_region"] = "us-east-1"
        payload["resources"][1]["provider_region"] = "us-west-2"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
