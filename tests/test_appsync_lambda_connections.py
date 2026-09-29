"""AppSync Lambda connections create scoped data sources and direct resolvers."""

from copy import deepcopy

import hcl2
import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.appsync_lambda import AppSyncLambdaConfig
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
        resolve_spec(ServiceType.APPSYNC, ServiceType.LAMBDA, None, {})
    )


def connection_file(tree, suffix):
    return next(value for path, value in tree.items() if path.endswith(suffix))


def test_direct_resolver_and_scoped_invoke_role_generated():
    payload = architecture()
    tree = generate(payload)
    source = connection_file(tree, "/lambda_datasource_target-resource.tf")
    resolver = next(
        value for path, value in tree.items() if "/lambda_resolver_Query_probe_" in path
    )
    main = tree["connection-check/environments/dev/main.tf"]
    assert 'resource "aws_iam_role" "lambda_target-resource_role"' in source
    assert 'Service = "appsync.amazonaws.com"' in source
    assert "aws_appsync_graphql_api.source-resource.arn" in source
    assert '"lambda:InvokeFunction"' in source
    assert "var.appsync_target-resource_function_arn" in source
    assert "aws_iam_role_policy.lambda_target-resource_invoke" in source
    assert 'type = "AWS_LAMBDA"' in source
    assert "aws_iam_role.lambda_target-resource_role.arn" in source
    assert 'resource "aws_appsync_resolver" "resolver_Query_probe_' in resolver
    assert 'type = "Query"' in resolver
    assert 'field = "probe"' in resolver
    assert "aws_appsync_datasource.lambda_target-resource.name" in resolver
    assert "request_template" not in resolver
    assert "response_template" not in resolver
    assert "module.target-resource.function_arn" in main
    assert generate(payload) == tree
    hcl2.loads(source)
    hcl2.loads(resolver)


def test_multiple_fields_share_one_data_source():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Query { probe: String, second: String }"
    )
    second = deepcopy(payload["connections"][0])
    second["connection_config"] = {"field_name": "second"}
    payload["connections"].append(second)
    tree = generate(payload)
    paths = list(tree)
    assert len([path for path in paths if "lambda_datasource_" in path]) == 1
    assert len([path for path in paths if "lambda_resolver_" in path]) == 2
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(second))
    assert generate(payload) == tree


def test_multiple_functions_have_distinct_roles_and_resolvers():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Query { probe: String, second: String }"
    )
    function = deepcopy(payload["resources"][1])
    function.update(id="second", name="other_function")
    function["config"]["function_name"] = "other-function"
    payload["resources"].append(function)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="other_function", target_id="second")
    connection["connection_config"] = {"field_name": "second"}
    payload["connections"].append(connection)
    tree = generate(payload)
    paths = list(tree)
    assert len([path for path in paths if "lambda_datasource_" in path]) == 2
    assert len([path for path in paths if "lambda_resolver_" in path]) == 2
    assert "module.other_function.function_arn" in "\n".join(tree.values())
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"][0]["connection_config"] = {"field_name": "probe"}
    with pytest.raises(InvalidConnectionConfigError, match="multiple Lambda resolvers"):
        generate(payload)


def test_function_names_with_hyphen_and_underscore_remain_distinct():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Query { probe: String, second: String }"
    )
    function = deepcopy(payload["resources"][1])
    function.update(id="second", name="target_resource")
    function["config"]["function_name"] = "other-function"
    payload["resources"].append(function)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="target_resource", target_id="second")
    connection["connection_config"] = {"field_name": "second"}
    payload["connections"].append(connection)
    tree = generate(payload)
    main = tree["connection-check/environments/dev/main.tf"]
    assert "appsync_target-resource_function_arn" in main
    assert "appsync_target_resource_function_arn" in main
    names = [
        path
        for path in tree
        if "/lambda_datasource_" in path or "/lambda_resolver_" in path
    ]
    assert len(names) == 4
    assert len(set(names)) == 4


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"field_name": "bad-name"},
        {"field_name": "__schema"},
        {"field_name": "probe", "type_name": "__Type"},
        {"field_name": "probe", "type_name": "1Query"},
    ],
)
def test_invalid_field_selection_rejected(config):
    with pytest.raises(ValidationError):
        AppSyncLambdaConfig.model_validate(config)


def test_schema_is_required_for_a_resolver():
    payload = architecture()
    payload["resources"][0]["config"].pop("schema_definition")
    with pytest.raises(InvalidConnectionConfigError, match="GraphQL schema definition"):
        generate(payload)


@needs_terraform
def test_appsync_lambda_project_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
