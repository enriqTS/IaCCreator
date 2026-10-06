"""Grafana OpenSearch queries preserve domain scope and native plugin settings."""

import hashlib
import json
import re
from copy import deepcopy
from fnmatch import fnmatchcase

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_opensearch import (
    opensearch_data_sources_expression,
    opensearch_scope_preconditions,
)
from app.models.connection_configs.grafana_opensearch import GrafanaOpenSearchConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_grafana_cloudwatch_connections import native_group
from tests.test_grafana_prometheus_connections import console, native_workspace
from tests.test_grafana_timestream_connections import (
    connect_other_sources,
    native_table,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.OPENSEARCH, None, {})
    )


def native_domain(region="us-east-1", name="application", index="application-records"):
    return {
        "arn": f"arn:aws:es:{region}:123456789012:domain/{name}",
        "domain_name": name,
        "region": region,
        "endpoint": f"search-{name}-abc123.{region}.es.amazonaws.com",
        "engine_version": "OpenSearch_2.19",
        "allow_explicit_index": "true",
        "index_name": index,
        "time_field": "@timestamp",
    }


def evaluate(tmp_path, expression, domains, partition="aws", dns="amazonaws.com"):
    replacements = {
        "var.opensearch_sources": json.dumps(domains),
        "var.prometheus_workspaces": json.dumps({"metrics": native_workspace()}),
        "var.cloudwatch_log_groups": json.dumps({"logs": native_group(encrypted=True)}),
        "var.timestream_tables": json.dumps({"data:cpu-load": native_table()}),
        "data.aws_partition.grafana_sources.partition": json.dumps(partition),
        "data.aws_partition.grafana_sources.dns_suffix": json.dumps(dns),
        "data.aws_caller_identity.grafana_sources.account_id": '"123456789012"',
    }
    for name, value in replacements.items():
        expression = expression.replace(name, value)
    (tmp_path / "payload.tf").write_text(f"locals {{\n  payload = {expression}\n}}\n")
    return json.loads(json.loads(console(tmp_path, "jsonencode(local.payload)")))


def connect_all_sources(payload):
    connect_other_sources(payload)
    template = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.TIMESTREAM, None, {})
    )
    payload["resources"].append(dict(template["resources"][1], name="time", id="time"))
    payload["connections"].append(
        dict(template["connections"][0], target="time", target_id="time")
    )


def connect_client(payload, source, kind, same_domain=True):
    template = connection_architecture(
        resolve_spec(source, ServiceType.OPENSEARCH, kind, {})
    )
    payload["resources"].append(
        dict(template["resources"][0], name="client", id="client")
    )
    connection = dict(template["connections"][0], source="client", source_id="client")
    if not same_domain:
        payload["resources"].append(
            dict(
                deepcopy(payload["resources"][1]),
                name="other-domain",
                id="other-domain",
            )
        )
        connection.update(target="other-domain", target_id="other-domain")
    payload["connections"].append(connection)


def test_native_domain_metadata_and_shared_role_have_separate_module_ownership():
    tree = generate(architecture())
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 4
    domain = resources(tree, "aws_opensearch_domain")[0]
    assert domain["advanced_options"] == {
        "rest.action.multi.allow_explicit_index": "true"
    }
    assert domain["domain_endpoint_options"][0]["enforce_https"] is True
    assert (
        domain["domain_endpoint_options"][0]["tls_security_policy"]
        == "Policy-Min-TLS-1-2-2019-07"
    )
    workspace = resources(tree, "aws_grafana_workspace")[0]
    assert workspace["role_arn"] == "${aws_iam_role.source-resource_data_sources.arn}"
    main = file_with(tree, "/environments/dev/main.tf")
    for output in [
        "domain_arn",
        "domain_endpoint",
        "grafana_domain_name",
        "grafana_domain_region",
        "grafana_engine_version",
        "grafana_explicit_index",
    ]:
        assert f"module.target-resource.{output}" in main
    assert 'time_field = "@timestamp"' in main
    target = file_with(tree, "/target-resource/outputs.tf")
    assert 'split(":", aws_opensearch_domain.target-resource.arn)[3]' in target
    assert "source-resource" not in target
    source = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "opensearch_data_sources"' in source
    assert "aws_iam_role_policy.source-resource_data_sources" in source
    assert not any(path.endswith("/iam.tf") for path in tree)


def test_standalone_domain_retains_its_existing_endpoint_settings():
    payload = architecture()
    payload["connections"] = []
    domain = resources(generate(payload), "aws_opensearch_domain")[0]
    assert "advanced_options" not in domain
    assert "domain_endpoint_options" not in domain


@given(
    bindings=st.lists(
        st.tuples(
            resource_name_st, st.from_regex(r"[a-z][a-z0-9_.-]{2,20}", fullmatch=True)
        ),
        min_size=1,
        max_size=6,
        unique=True,
    ),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_indexes_and_domains_aggregate_without_order_or_duplicate_dependencies(
    bindings, duplicate
):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in sorted({name for name, _ in bindings}):
        payload["resources"].append(
            dict(deepcopy(target), name=f"data-{name}", id=name)
        )
    for name, index in bindings:
        payload["connections"].append(
            dict(
                connection,
                target=f"data-{name}",
                target_id=name,
                connection_config={"index_name": index},
            )
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_opensearch_domain")) == len(
        {name for name, _ in bindings}
    )
    main = file_with(tree, "/environments/dev/main.tf")
    for name, index in bindings:
        assert f'"data-{name}:{index}" = ' in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "field,value",
    [
        ("index_name", None),
        ("index_name", ""),
        ("index_name", "logs*"),
        ("index_name", "UPPER"),
        ("index_name", "logs/index"),
        ("index_name", "a" * 256),
        ("time_field", ""),
        ("time_field", "field/*"),
        ("time_field", "${var.field}"),
        ("time_field", "a" * 256),
    ],
)
def test_invalid_defaults_cannot_expand_iam_paths_or_interpolate_terraform(
    field, value
):
    payload = architecture()
    if value is None:
        payload["connections"][0]["connection_config"].pop(field)
    else:
        payload["connections"][0]["connection_config"][field] = value
    with pytest.raises(InvalidConnectionConfigError, match=field):
        generate(payload)


def test_same_binding_rejects_conflicting_time_field_defaults():
    payload = architecture()
    config = dict(
        payload["connections"][0]["connection_config"], time_field="event.created"
    )
    payload["connections"].append(
        dict(payload["connections"][0], connection_config=config)
    )
    for connections in [payload["connections"], list(reversed(payload["connections"]))]:
        payload["connections"] = connections
        with pytest.raises(
            InvalidConnectionConfigError, match="conflicting time-field"
        ):
            generate(payload)


@pytest.mark.parametrize(
    "source,kind",
    [
        (ServiceType.LAMBDA, "reads_from"),
        (ServiceType.LAMBDA, "writes_to"),
        (ServiceType.ECS, "reads_from"),
        (ServiceType.ECS, "writes_to"),
        (ServiceType.APPSYNC, "resolves_with"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_index_scoped_clients_on_same_domain_are_rejected_in_any_order(
    source, kind, reverse
):
    payload = architecture()
    connect_client(payload, source, kind)
    if reverse:
        payload["connections"].reverse()
    with pytest.raises(
        InvalidConnectionConfigError, match="explicit request-body indexes"
    ):
        generate(payload)


def test_separate_domains_keep_grafana_and_runtime_clients_independent():
    payload = architecture()
    connect_client(payload, ServiceType.LAMBDA, "reads_from", same_domain=False)
    domains = resources(generate(payload), "aws_opensearch_domain")
    assert [
        domain["advanced_options"]["rest.action.multi.allow_explicit_index"]
        for domain in domains
    ] == ["true", "false"]


def test_all_data_sources_share_one_complete_role_and_each_workspace_owns_its_role():
    payload = architecture()
    connect_all_sources(payload)
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 14
    for action in [
        "es:ESHttpPost",
        "timestream:Select",
        "aps:QueryMetrics",
        "logs:StartQuery",
        "kms:Decrypt",
    ]:
        assert action in policy["policy"]
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["resources"].append(
        dict(deepcopy(payload["resources"][0]), name="other", id="other")
    )
    connection = next(
        item for item in payload["connections"] if item["target"] == "target-resource"
    )
    payload["connections"].append(dict(connection, source="other", source_id="other"))
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 2
    assert len(resources(tree, "aws_opensearch_domain")) == 1


def test_preview_and_catalog_explain_domain_access_and_external_setup():
    spec = resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.OPENSEARCH, None, {})
    assert spec.config_model is GrafanaOpenSearchConfig
    assert spec.connection_type == "queries" and spec.region_policy == "cross-region"
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    messages = "\n".join(item.message for item in preview.issues)
    for text in [
        "any index",
        "not an IAM boundary",
        "incompatible",
        "date mappings",
        "fine-grained",
        "network reachability",
        "compatible plugin",
        "PPL, SQL",
    ]:
        assert text in messages
    assert not preview.iam
    assert {item.module for item in preview.resources} == {"source-resource"}


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("same", [True] * 4),
        ("cross_region", [True] * 4),
        ("private", [True] * 4),
        ("cross_account", [True, False, True, True]),
        ("cross_partition", [True, False, True, True]),
        ("invalid_arn", [False, False, False, True]),
        ("wildcard_index", [False, True, True, True]),
        ("wildcard_field", [False, True, True, True]),
        ("wrong_region", [True, True, False, True]),
        ("wrong_name", [True, True, False, True]),
        ("wrong_endpoint", [True, True, False, True]),
        ("custom_endpoint", [True, True, False, True]),
        ("explicit_false", [True, True, True, False]),
        ("invalid_version", [True, True, True, False]),
        ("empty", [False, True, True, True]),
    ],
)
def test_native_guards_reject_identity_and_protocol_mismatches(
    tmp_path, mode, expected
):
    domain = native_domain()
    if mode == "cross_region":
        domain = native_domain(region="eu-west-1")
    elif mode == "private":
        domain["endpoint"] = domain["endpoint"].replace("search-", "vpc-", 1)
    elif mode == "cross_account":
        domain["arn"] = domain["arn"].replace("123456789012", "999999999999")
    elif mode == "cross_partition":
        domain["arn"] = domain["arn"].replace("arn:aws:", "arn:aws-us-gov:")
    elif mode == "invalid_arn":
        domain["arn"] = "invalid"
    elif mode == "wildcard_index":
        domain["index_name"] = "logs*"
    elif mode == "wildcard_field":
        domain["time_field"] = "field/*"
    elif mode == "wrong_region":
        domain["region"] = "eu-west-1"
    elif mode == "wrong_name":
        domain["domain_name"] = "another"
    elif mode == "wrong_endpoint":
        domain["endpoint"] = "search-other-abc123.us-east-1.es.amazonaws.com"
    elif mode == "custom_endpoint":
        domain["endpoint"] = (
            "https://search-application-abc123.us-east-1.es.amazonaws.com"
        )
    elif mode == "explicit_false":
        domain["allow_explicit_index"] = "false"
    elif mode == "invalid_version":
        domain["engine_version"] = "OpenSearch_latest"
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in opensearch_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(tmp_path, expression, {} if mode == "empty" else {"data:logs": domain})
        == expected
    )


@needs_terraform
@pytest.mark.parametrize(
    "partition,region,dns",
    [
        ("aws-cn", "cn-north-1", "amazonaws.com.cn"),
        ("aws-us-gov", "us-gov-west-1", "amazonaws.com"),
    ],
)
def test_native_dns_guards_support_other_aws_partitions(
    tmp_path, partition, region, dns
):
    domain = native_domain(region=region)
    domain["arn"] = domain["arn"].replace("arn:aws:", f"arn:{partition}:")
    domain["endpoint"] = domain["endpoint"].replace("amazonaws.com", dns)
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in opensearch_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(tmp_path, expression, {"data:logs": domain}, partition, dns)
        == [True] * 4
    )


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
def test_serialized_iam_grants_only_metadata_and_domain_root_multi_search(
    tmp_path, mixed
):
    payload = architecture()
    if mixed:
        connect_all_sources(payload)
    text = file_with(generate(payload), "/source-resource/data_source_role.tf")
    expression = re.search(
        r"\n  policy = (jsonencode\(.*?\))\n  lifecycle", text, re.S
    ).group(1)
    first = native_domain()
    second = native_domain(index="memory")
    remote = native_domain(region="eu-west-1", name="remote")
    policy = json.loads(
        evaluate(
            tmp_path,
            expression,
            {"data:logs": first, "data:memory": second, "remote:logs": remote},
        )
    )
    statements = policy["Statement"]
    assert all(isinstance(item, dict) for item in statements)
    by_sid = {item.get("Sid"): item for item in statements}
    assert by_sid["OpenSearchVersion"]["Resource"] == [
        first["arn"] + "/",
        remote["arn"] + "/",
    ]
    assert by_sid["OpenSearchMultiSearch"]["Resource"] == [
        first["arn"] + "/_msearch",
        remote["arn"] + "/_msearch",
    ]

    def allows(action, arn):
        return any(
            action
            in (
                item["Action"] if isinstance(item["Action"], list) else [item["Action"]]
            )
            and any(
                fnmatchcase(arn, resource)
                for resource in (
                    item["Resource"]
                    if isinstance(item["Resource"], list)
                    else [item["Resource"]]
                )
            )
            for item in statements
        )

    for path in [
        "/",
        "/application-records/_mapping",
        "/application-records/_mapping/field/@timestamp",
        "/memory/_field_caps",
        "/application-records/_settings/index.number_of_shards",
    ]:
        assert allows("es:ESHttpGet", first["arn"] + path)
    assert allows("es:ESHttpPost", first["arn"] + "/_msearch")
    for path in [
        "/_bulk",
        "/_plugins/_ppl",
        "/_plugins/_sql",
        "/application-records/_doc/1",
        "/application-records/_msearch",
        "/_msearch/extra",
    ]:
        assert not allows("es:ESHttpPost", first["arn"] + path)
    for path in [
        "/_cat/indices",
        "/_cluster/health",
        "/other/_mapping",
        "/other/_search",
    ]:
        assert not allows("es:ESHttpGet", first["arn"] + path)
    assert not allows(
        "es:ESHttpPost",
        first["arn"].replace("application", "unconnected") + "/_msearch",
    )
    for action in ["es:ESHttpPut", "es:ESHttpDelete", "es:UpdateDomainConfig"]:
        assert not allows(action, first["arn"] + "/_msearch")
    assert ("TimestreamTableQueries" in by_sid) is mixed


@needs_terraform
@pytest.mark.parametrize(
    "engine,flavor,version",
    [
        ("OpenSearch_2.19", "opensearch", "2.19.0"),
        ("OpenSearch_2.19.1", "opensearch", "2.19.1"),
        ("Elasticsearch_7.10", "elasticsearch", "7.10.0"),
    ],
)
def test_exported_settings_use_native_endpoint_version_region_and_stable_uids(
    tmp_path, engine, flavor, version
):
    native = native_domain(region="eu-west-1", index="logs.2026")
    native.update(engine_version=engine, time_field="event.created")
    expression = str(opensearch_data_sources_expression())
    payloads = evaluate(tmp_path, expression, {"data:logs.2026": native})
    item = payloads["data:logs.2026"]
    assert item == {
        "name": "data:logs.2026",
        "uid": "os-"
        + hashlib.sha256(f"{native['arn']}/index/logs.2026".encode()).hexdigest()[:16],
        "type": "grafana-opensearch-datasource",
        "access": "proxy",
        "url": f"https://{native['endpoint']}",
        "jsonData": {
            "flavor": flavor,
            "version": version,
            "database": "logs.2026",
            "timeField": "event.created",
            "timeInterval": "10s",
            "pplEnabled": False,
            "serverless": False,
            "sigV4Auth": True,
            "sigV4AuthType": "default",
            "sigV4Region": "eu-west-1",
        },
    }
    renamed = evaluate(tmp_path, expression, {"renamed:logs.2026": native})
    assert renamed["renamed:logs.2026"]["uid"] == item["uid"]


@needs_terraform
@pytest.mark.parametrize("length", [188, 189, 255])
def test_long_index_names_preserve_defaults_and_distinct_bounded_display_names(
    tmp_path, length
):
    domains = {
        f"d:{'a' * length}": native_domain(index="a" * length),
        f"d:{'a' * (length - 1)}b": native_domain(index="a" * (length - 1) + "b"),
    }
    payload = architecture()
    payload["connections"][0]["connection_config"]["index_name"] = "a" * length
    generate(payload)
    payloads = evaluate(tmp_path, str(opensearch_data_sources_expression()), domains)
    assert len({item["name"] for item in payloads.values()}) == 2
    assert len({item["uid"] for item in payloads.values()}) == 2
    for binding, native in domains.items():
        assert len(payloads[binding]["name"]) <= 190
        assert payloads[binding]["jsonData"]["database"] == native["index_name"]
        assert payloads[binding]["name"] == (
            binding
            if len(binding) <= 190
            else binding[:173] + "-" + hashlib.sha256(binding.encode()).hexdigest()[:16]
        )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode", ["plain", "cross_region", "multiple_indexes", "mixed", "separate_client"]
)
def test_generated_projects_validate_and_have_acyclic_shared_role_graphs(
    tmp_path, mode
):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "multiple_indexes":
        payload["connections"].append(
            dict(payload["connections"][0], connection_config={"index_name": "memory"})
        )
    elif mode == "mixed":
        connect_all_sources(payload)
    elif mode == "separate_client":
        connect_client(payload, ServiceType.LAMBDA, "reads_from", same_domain=False)
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    path = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], path.parent
    )
    _run_terraform(["validate", "-no-color"], path.parent)
    _run_terraform(["graph", "-type=plan"], path.parent)
