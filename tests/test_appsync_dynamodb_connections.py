"""AppSync DynamoDB connections create item resolvers with scoped access."""

import json
from copy import deepcopy

import hcl2
import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.appsync_dynamodb import AppSyncDynamoDbConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_appsync_lambda_connections import architecture as lambda_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate
from tests.test_kms_access_integration import add_key


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.APPSYNC, ServiceType.DYNAMODB, None, {})
    )


def file_with(tree, needle):
    return next(value for path, value in tree.items() if needle in path)


def resolver_code(hcl):
    resource = hcl2.loads(hcl)["resource"][0]['"aws_appsync_resolver"']
    attributes = next(iter(resource.values()))
    return json.loads(attributes["code"])


@pytest.mark.parametrize(
    "operation,settings,method,action",
    [
        ("get_item", {"consistent_read": True}, "get", "GetItem"),
        ("put_item", {}, "put", "PutItem"),
        ("update_item", {"update_attribute": "title"}, "update", "UpdateItem"),
        ("delete_item", {}, "remove", "DeleteItem"),
    ],
)
def test_item_resolver_and_operation_scoped_policy(operation, settings, method, action):
    payload = architecture()
    if operation != "get_item":
        payload["resources"][0]["config"]["schema_definition"] = (
            "type Query { noop: String } "
            "type Item { id: ID!, title: String } "
            "type Mutation { probe(id: ID!, input: ItemInput, value: String): Item } "
            "input ItemInput { title: String }"
        )
    payload["connections"][0]["connection_config"] = {
        "field_name": "probe",
        "operation": operation,
        **settings,
    }
    tree = generate(payload)
    source = file_with(tree, "/dynamodb_datasource_target-resource.tf")
    resolver = file_with(tree, "/dynamodb_resolver_")
    code = resolver_code(resolver)
    main = tree["connection-check/environments/dev/main.tf"]
    assert 'Service = "appsync.amazonaws.com"' in source
    assert "aws_appsync_graphql_api.source-resource.arn" in source
    assert f'"dynamodb:{action}"' in source
    assert "var.appsync_target-resource_table_arn" in source
    assert 'type = "AMAZON_DYNAMODB"' in source
    assert "var.appsync_target-resource_table_name" in source
    assert "aws_iam_role_policy.dynamodb_target-resource_access" in source
    assert f"ddb.{method}(" in code
    assert '"id": ctx.args["id"]' in code
    assert 'name = "APPSYNC_JS"' in resolver
    assert 'runtime_version = "1.0.0"' in resolver
    assert "module.target-resource.table_name" in main
    assert "module.target-resource.table_arn" in main
    if operation == "put_item":
        assert "attributeExists: false" in code
    if operation == "update_item":
        assert "ddb.operations.replace" in code
        assert "attributeExists: true" in code
    assert generate(payload) == tree
    hcl2.loads(source)
    hcl2.loads(resolver)


def test_composite_key_and_custom_graphql_arguments():
    payload = architecture()
    payload["resources"][1]["config"].update(
        hash_key="pk", range_key="sk", range_key_type="S"
    )
    payload["connections"][0]["connection_config"] = {
        "field_name": "probe",
        "hash_argument": "partition",
        "range_argument": "sort",
    }
    code = resolver_code(file_with(generate(payload), "/dynamodb_resolver_"))
    assert '"pk": ctx.args["partition"]' in code
    assert '"sk": ctx.args["sort"]' in code


def test_put_overwrite_uses_configured_item_argument():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "field_name": "probe",
        "operation": "put_item",
        "item_argument": "record",
        "overwrite": True,
    }
    code = resolver_code(file_with(generate(payload), "/dynamodb_resolver_"))
    assert 'item: ctx.args["record"]' in code
    assert "attributeExists" not in code


def test_multiple_fields_share_a_table_role_and_aggregate_actions():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID!, title: String } "
        "type Query { probe(id: ID!): Item } "
        "type Mutation { create(id: ID!, input: ItemInput!): Item } "
        "input ItemInput { title: String }"
    )
    second = deepcopy(payload["connections"][0])
    second["connection_config"] = {"field_name": "create", "operation": "put_item"}
    payload["connections"].append(second)
    tree = generate(payload)
    source = file_with(tree, "/dynamodb_datasource_target-resource.tf")
    assert '"dynamodb:GetItem"' in source
    assert '"dynamodb:PutItem"' in source
    assert len([p for p in tree if "/dynamodb_datasource_" in p]) == 1
    assert len([p for p in tree if "/dynamodb_resolver_" in p]) == 2
    assert 'type = "Mutation"' in file_with(tree, "/dynamodb_resolver_Mutation_")
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(second))
    assert generate(payload) == tree


def test_multiple_tables_use_separate_data_sources():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID!, title: String } "
        "type Query { probe(id: ID!): Item, second(id: ID!): Item }"
    )
    table = deepcopy(payload["resources"][1])
    table.update(id="second", name="other_table")
    table["config"]["table_name"] = "other-table"
    payload["resources"].append(table)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="other_table", target_id="second")
    connection["connection_config"] = {"field_name": "second"}
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len([p for p in tree if "/dynamodb_datasource_" in p]) == 2
    assert "module.other_table.table_arn" in "\n".join(tree.values())
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"][0]["connection_config"] = {"field_name": "probe"}
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple DynamoDB resolvers"
    ):
        generate(payload)


def test_lambda_and_dynamodb_cannot_resolve_the_same_field():
    payload = lambda_architecture()
    table = deepcopy(architecture()["resources"][1])
    table.update(id="table", name="items")
    payload["resources"].append(table)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="items", target_id="table")
    payload["connections"].append(connection)
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple data-source resolvers"
    ):
        generate(payload)


def test_lambda_and_dynamodb_resolve_distinct_fields():
    payload = lambda_architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID! } type Query { probe: String, item(id: ID!): Item }"
    )
    table = deepcopy(architecture()["resources"][1])
    table.update(id="table", name="items")
    payload["resources"].append(table)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="items", target_id="table")
    connection["connection_config"] = {"field_name": "item"}
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len([p for p in tree if "/lambda_resolver_" in p]) == 1
    assert len([p for p in tree if "/dynamodb_resolver_" in p]) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"field_name": "bad-name"},
        {"field_name": "__schema"},
        {"field_name": "probe", "operation": "scan"},
        {"field_name": "probe", "operation": "update_item"},
        {"field_name": "probe", "operation": "get_item", "overwrite": True},
        {"field_name": "probe", "operation": "put_item", "consistent_read": True},
        {"field_name": "probe", "operation": "get_item", "update_attribute": "title"},
    ],
)
def test_invalid_field_or_operation_rejected(settings):
    with pytest.raises(ValidationError):
        AppSyncDynamoDbConfig.model_validate(settings)


def test_invalid_table_key_and_missing_schema_rejected():
    payload = architecture()
    payload["resources"][0]["config"].pop("schema_definition")
    with pytest.raises(InvalidConnectionConfigError, match="GraphQL schema definition"):
        generate(payload)
    payload = architecture()
    payload["connections"][0]["connection_config"]["range_argument"] = "sort"
    with pytest.raises(InvalidConnectionConfigError, match="sort key"):
        generate(payload)
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        operation="update_item", update_attribute="id"
    )
    with pytest.raises(InvalidConnectionConfigError, match="key attribute"):
        generate(payload)


@pytest.mark.parametrize("managed", [False, True])
def test_encrypted_table_adds_key_scoped_grant(managed):
    payload = architecture()
    if managed:
        add_key(payload)
    else:
        payload["resources"][1]["config"].update(
            server_side_encryption_enabled=True,
            server_side_encryption_kms_key_arn="alias/external-key",
        )
    source = file_with(generate(payload), "/dynamodb_datasource_target-resource.tf")
    assert '"kms:Decrypt"' in source
    if managed:
        assert "var.appsync_target-resource_kms_key_arn" in source
    else:
        assert "data.aws_kms_key.appsync_target-resource_kms_key_id.arn" in source


def test_encrypted_writes_add_data_key_permission():
    payload = architecture()
    add_key(payload)
    payload["connections"][0]["connection_config"] = {
        "field_name": "probe",
        "operation": "put_item",
    }
    source = file_with(generate(payload), "/dynamodb_datasource_target-resource.tf")
    assert '"kms:Decrypt"' in source
    assert '"kms:GenerateDataKey"' in source


def test_external_key_without_table_encryption_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["server_side_encryption_kms_key_arn"] = (
        "alias/external-key"
    )
    with pytest.raises(InvalidConnectionConfigError, match="server-side encryption"):
        generate(payload)


@needs_terraform
@pytest.mark.parametrize("encryption", ["none", "managed", "external"])
def test_appsync_dynamodb_project_validates(tmp_path, encryption):
    payload = architecture()
    if encryption == "managed":
        add_key(payload)
    elif encryption == "external":
        payload["resources"][1]["config"].update(
            server_side_encryption_enabled=True,
            server_side_encryption_kms_key_arn="alias/external-key",
        )
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
