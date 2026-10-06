"""AppSync Aurora connections generate Data API resolvers and scoped credentials."""

import json
from copy import deepcopy

import hcl2
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.appsync_aurora import AppSyncAuroraConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_appsync_dynamodb_connections import (
    architecture as dynamodb_architecture,
)
from tests.test_appsync_eventbridge_connections import (
    architecture as eventbridge_architecture,
)
from tests.test_appsync_lambda_connections import architecture as lambda_architecture
from tests.test_appsync_opensearch_connections import (
    architecture as opensearch_architecture,
)
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.APPSYNC, ServiceType.AURORA, None, {})
    )


def file_with(tree, needle):
    return next(value for path, value in tree.items() if needle in path)


def resolver_code(tree, needle="/aurora_resolver_"):
    resolver = file_with(tree, needle)
    resource = hcl2.loads(resolver)["resource"][0]['"aws_appsync_resolver"']
    return json.loads(next(iter(resource.values()))["code"])


def test_cluster_data_api_and_scoped_appsync_source_generated():
    tree = generate(architecture())
    cluster = file_with(tree, "/aurora/target-resource/aurora.tf")
    outputs = file_with(tree, "/aurora/target-resource/outputs.tf")
    source = file_with(tree, "/aurora_datasource_target-resource.tf")
    resolver = file_with(tree, "/aurora_resolver_Query_probe_")
    code = resolver_code(tree)
    main = tree["connection-check/environments/dev/main.tf"]
    assert 'engine_mode = "provisioned"' in cluster
    assert "enable_http_endpoint = true" in cluster
    assert "storage_encrypted = true" in cluster
    assert "manage_master_user_password = true" in cluster
    assert "serverlessv2_scaling_configuration" in cluster
    assert 'instance_class = "db.serverless"' in cluster
    assert "publicly_accessible = false" in cluster
    assert "aws_rds_cluster_instance.target-resource_writer" in outputs
    assert "master_user_secret[0].secret_arn" in outputs
    assert "module.target-resource.data_api_cluster_arn" in main
    assert "module.target-resource.database_name" in main
    assert 'Service = "appsync.amazonaws.com"' in source
    assert "aws_appsync_graphql_api.source-resource.arn" in source
    assert '"rds-data:ExecuteStatement"' in source
    assert "var.appsync_target-resource_cluster_arn" in source
    assert '"secretsmanager:GetSecretValue"' in source
    assert "app-user-Ab12Cd" in source
    assert "master_secret_arn" not in source
    assert 'type = "RELATIONAL_DATABASE"' in source
    assert 'source_type = "RDS_HTTP_ENDPOINT"' in source
    assert "aws_iam_role_policy.aurora_target-resource_access" in source
    assert "createPgStatement(select(" in code
    assert 'table: "items"' in code
    assert '"id": { eq: ctx.args["id"] }' in code
    assert "toJsonObject(ctx.result)?.[0]?.[0]" in code
    assert 'name = "APPSYNC_JS"' in resolver
    assert generate(architecture()) == tree
    hcl2.loads(cluster)
    hcl2.loads(source)
    hcl2.loads(resolver)


@pytest.mark.parametrize(
    "operation,method,result",
    [
        ("get_row", "select", "?.[0]?.[0]"),
        ("list_rows", "select", "?.[0] || []"),
        ("insert_row", "insert", "?.[0]?.[0]"),
        ("update_row", "update", "?.[0]?.[0]"),
        ("delete_row", "remove", "?.[0]?.[0]"),
    ],
)
def test_parameterized_sql_operations(operation, method, result):
    payload = architecture()
    payload["connections"][0]["connection_config"]["operation"] = operation
    code = resolver_code(generate(payload))
    assert f"createPgStatement({method}(" in code
    assert result in code
    assert 'table: "items"' in code
    if operation == "list_rows":
        assert "limit: 50" in code
    if operation in {"insert_row", "update_row"}:
        assert 'ctx.args["input"]' in code
        assert "returning: '*'" in code
    if operation == "update_row":
        assert 'delete values["id"]' in code
    if operation in {"get_row", "update_row", "delete_row"}:
        assert 'eq: ctx.args["id"]' in code


def test_multiple_fields_share_one_data_source():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID!, title: String } "
        "type Query { probe(id: ID!): Item, items: [Item] } "
        "type Mutation { save(input: ItemInput!): Item } "
        "input ItemInput { id: ID!, title: String }"
    )
    listed = deepcopy(payload["connections"][0])
    listed["connection_config"].update(field_name="items", operation="list_rows")
    inserted = deepcopy(payload["connections"][0])
    inserted["connection_config"].update(field_name="save", operation="insert_row")
    payload["connections"].extend([listed, inserted])
    tree = generate(payload)
    assert len([p for p in tree if "/aurora_datasource_" in p]) == 1
    assert len([p for p in tree if "/aurora_resolver_" in p]) == 3
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(listed))
    assert generate(payload) == tree


def test_multiple_clusters_have_separate_data_sources():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID! } "
        "type Query { probe(id: ID!): Item, second(id: ID!): Item }"
    )
    cluster = deepcopy(payload["resources"][1])
    cluster.update(id="other", name="other-cluster")
    cluster["config"]["cluster_identifier"] = "other-cluster"
    payload["resources"].append(cluster)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="other-cluster", target_id="other")
    connection["connection_config"]["field_name"] = "second"
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len([p for p in tree if "/aurora_datasource_" in p]) == 2
    assert "module.other-cluster.data_api_cluster_arn" in "\n".join(tree.values())


def test_conflicting_field_and_credential_rejected():
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"]["table_name"] = "other_table"
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="multiple Aurora resolvers"):
        generate(payload)
    payload["connections"][1]["connection_config"].update(
        field_name="other",
        credential_secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:other-Ab12Cd",
    )
    with pytest.raises(
        InvalidConnectionConfigError, match="one database-user credential"
    ):
        generate(payload)


@pytest.mark.parametrize(
    "other_architecture",
    [
        lambda_architecture,
        dynamodb_architecture,
        opensearch_architecture,
        eventbridge_architecture,
    ],
)
def test_other_data_sources_cannot_resolve_same_field(other_architecture):
    payload = other_architecture()
    cluster = deepcopy(architecture()["resources"][1])
    cluster.update(id="database", name="database")
    payload["resources"].append(cluster)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="database", target_id="database")
    connection["connection_config"]["type_name"] = (
        "Mutation" if other_architecture is eventbridge_architecture else "Query"
    )
    payload["connections"].append(connection)
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple data-source resolvers"
    ):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("engine", "aurora-mysql"),
        ("engine_version", None),
        ("database_name", None),
        ("database_name", "invalid-name"),
    ],
)
def test_unsupported_or_incomplete_cluster_rejected(field, value):
    payload = architecture()
    payload["resources"][1]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_missing_schema_and_standalone_rds_unsupported():
    payload = architecture()
    payload["resources"][0]["config"].pop("schema_definition")
    with pytest.raises(InvalidConnectionConfigError, match="GraphQL schema definition"):
        generate(payload)
    assert resolve_spec(ServiceType.APPSYNC, ServiceType.RDS, None, {}) is None


def test_customer_managed_secret_key_adds_decrypt_grant():
    payload = architecture()
    payload["connections"][0]["connection_config"]["credential_kms_key_arn"] = (
        "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789abc"
    )
    source = file_with(generate(payload), "/aurora_datasource_target-resource.tf")
    assert '"kms:Decrypt"' in source
    assert "key/12345678-1234-1234-1234-123456789abc" in source


@pytest.mark.parametrize("field", ["credential_secret_arn", "credential_kms_key_arn"])
def test_cross_region_credentials_rejected(field):
    payload = architecture()
    if field == "credential_secret_arn":
        payload["connections"][0]["connection_config"][field] = (
            "arn:aws:secretsmanager:eu-west-1:123456789012:secret:app-user-Ab12Cd"
        )
    else:
        payload["connections"][0]["connection_config"][field] = (
            "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789abc"
        )
    with pytest.raises(InvalidConnectionConfigError, match="Region"):
        generate(payload)


def test_unconnected_aurora_does_not_gain_data_api_resources():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    cluster = file_with(tree, "/aurora/target-resource/aurora.tf")
    assert "enable_http_endpoint" not in cluster
    assert "aws_rds_cluster_instance" not in cluster
    assert "data_api_cluster_arn" not in "\n".join(tree.values())


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"field_name": "bad-name"},
        {"field_name": "__schema"},
        {"field_name": "probe", "table_name": "users;DROP TABLE"},
        {"field_name": "probe", "table_name": "one,two"},
        {
            "field_name": "probe",
            "table_name": "users",
            "credential_secret_arn": "secret",
        },
    ],
)
def test_invalid_config_rejected(settings):
    with pytest.raises(ValidationError):
        AppSyncAuroraConfig.model_validate(settings)


@given(
    table=st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,15}", fullmatch=True),
    column=st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,15}", fullmatch=True),
)
def test_identifiers_remain_static_and_parameterized(table, column):
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        table_name=table, id_column=column
    )
    code = resolver_code(generate(payload))
    assert f'table: "{table}"' in code
    assert f'"{column}": {{ eq: ctx.args["id"] }}' in code


@needs_terraform
def test_appsync_aurora_project_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
