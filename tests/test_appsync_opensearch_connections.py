"""AppSync OpenSearch connections bind index-scoped document resolvers."""

import json
from copy import deepcopy

import hcl2
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.appsync_opensearch import AppSyncOpenSearchConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_appsync_dynamodb_connections import (
    architecture as dynamodb_architecture,
)
from tests.test_appsync_lambda_connections import architecture as lambda_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.APPSYNC, ServiceType.OPENSEARCH, None, {})
    )


def file_with(tree, needle):
    return next(value for path, value in tree.items() if needle in path)


@pytest.mark.parametrize(
    "operation,method,path,type_name",
    [
        ("get_document", "Get", "/_doc/*", "Query"),
        ("search", "Post", "/_search", "Query"),
        ("index_document", "Put", "/_doc/*", "Mutation"),
        ("delete_document", "Delete", "/_doc/*", "Mutation"),
    ],
)
def test_resolver_and_policy_are_scoped_to_selected_operation(
    operation, method, path, type_name
):
    payload = architecture()
    payload["connections"][0]["connection_config"]["operation"] = operation
    tree = generate(payload)
    source = file_with(tree, "/opensearch_datasource_target-resource.tf")
    resolver = file_with(tree, f"/opensearch_resolver_{type_name}_probe_")
    resource = hcl2.loads(resolver)["resource"][0]['"aws_appsync_resolver"']
    code = json.loads(next(iter(resource.values()))["code"])
    main = tree["connection-check/environments/dev/main.tf"]
    domain = file_with(tree, "/opensearch/target-resource/opensearch.tf")
    assert 'Service = "appsync.amazonaws.com"' in source
    assert "aws_appsync_graphql_api.source-resource.arn" in source
    assert f'"es:ESHttp{method}"' in source
    assert f"%s/application-records{path}" in source
    assert 'type = "AMAZON_OPENSEARCH_SERVICE"' in source
    assert "https://%s" in source
    assert "aws_iam_role_policy.opensearch_target-resource_access" in source
    assert "module.target-resource.domain_arn" in main
    assert "module.target-resource.domain_endpoint" in main
    assert "rest.action.multi.allow_explicit_index" in domain
    assert "enforce_https = true" in domain
    assert 'name = "APPSYNC_JS"' in resolver
    assert f'type = "{type_name}"' in resolver
    assert "if (ctx.error) util.error" in code
    if operation == "search":
        assert "simple_query_string" in code
        assert 'ctx.args["query"]' in code
        assert "hits.hits.map" in code
    else:
        assert "util.matches" in code
        assert "util.urlEncode(id)" in code
    if operation == "index_document":
        assert 'ctx.args["input"]' in code
    assert generate(payload) == tree
    hcl2.loads(source)
    hcl2.loads(resolver)


def test_multiple_fields_share_one_domain_data_source_and_aggregate_grants():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID! } "
        "type Query { probe(query: String!): [Item], item(id: ID!): Item } "
        "type Mutation { save(id: ID!, input: ItemInput!): AWSJSON } "
        "input ItemInput { id: ID! }"
    )
    lookup = deepcopy(payload["connections"][0])
    lookup["connection_config"] = {
        "index_name": "application-records",
        "field_name": "item",
        "operation": "get_document",
    }
    write = deepcopy(lookup)
    write["connection_config"] = {
        "index_name": "other-index",
        "field_name": "save",
        "operation": "index_document",
    }
    payload["connections"].extend([lookup, write])
    tree = generate(payload)
    source = file_with(tree, "/opensearch_datasource_target-resource.tf")
    assert len([p for p in tree if "/opensearch_datasource_" in p]) == 1
    assert len([p for p in tree if "/opensearch_resolver_" in p]) == 3
    for grant in (
        "application-records/_search",
        "application-records/_doc/*",
        "other-index/_doc/*",
    ):
        assert grant in source
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(lookup))
    assert generate(payload) == tree


def test_multiple_domains_are_isolated_and_field_conflicts_fail():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Item { id: ID! } type Query { probe(query: String!): [Item], second(query: String!): [Item] }"
    )
    domain = deepcopy(payload["resources"][1])
    domain.update(id="other", name="other-domain")
    domain["config"]["domain_name"] = "other-domain"
    payload["resources"].append(domain)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="other-domain", target_id="other")
    connection["connection_config"]["field_name"] = "second"
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len([p for p in tree if "/opensearch_datasource_" in p]) == 2
    assert "module.other-domain.domain_arn" in "\n".join(tree.values())
    payload["connections"][0]["connection_config"]["field_name"] = "second"
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple OpenSearch resolvers"
    ):
        generate(payload)


@pytest.mark.parametrize(
    "other_architecture", [lambda_architecture, dynamodb_architecture]
)
def test_other_data_sources_cannot_resolve_same_field(other_architecture):
    payload = other_architecture()
    domain = deepcopy(architecture()["resources"][1])
    domain.update(id="search", name="search-domain")
    payload["resources"].append(domain)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="search-domain", target_id="search")
    payload["connections"].append(connection)
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple data-source resolvers"
    ):
        generate(payload)


def test_missing_schema_rejected():
    payload = architecture()
    payload["resources"][0]["config"].pop("schema_definition")
    with pytest.raises(InvalidConnectionConfigError, match="GraphQL schema definition"):
        generate(payload)


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"field_name": "probe", "index_name": "Uppercase"},
        {"field_name": "probe", "index_name": "logs-*"},
        {"field_name": "probe", "index_name": "logs,other"},
        {"field_name": "probe", "index_name": "logs/foo"},
        {"field_name": "__schema", "index_name": "logs"},
        {"field_name": "probe", "index_name": "logs", "id_argument": "__id"},
        {"field_name": "probe", "index_name": "logs", "operation": "bulk"},
    ],
)
def test_invalid_config_rejected(settings):
    with pytest.raises(ValidationError):
        AppSyncOpenSearchConfig.model_validate(settings)


@given(
    index=st.from_regex(r"[a-z][a-z0-9_-]{0,20}", fullmatch=True),
    field=st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,20}", fullmatch=True),
)
def test_valid_names_remain_literal_paths_and_fields(index, field):
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        index_name=index, field_name=field
    )
    tree = generate(payload)
    assert f"%s/{index}/_search" in file_with(
        tree, "/opensearch_datasource_target-resource.tf"
    )
    assert f'field = "{field}"' in file_with(tree, "/opensearch_resolver_")


@needs_terraform
def test_appsync_opensearch_project_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
