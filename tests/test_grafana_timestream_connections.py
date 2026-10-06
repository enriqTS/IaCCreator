"""Timestream Grafana grants isolate selected tables and preserve source composition."""

import hashlib
import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_timestream import (
    timestream_data_sources_expression,
    timestream_scope_preconditions,
)
from app.models.connection_configs.table_access import TimestreamTableAccessConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cloudtrail_logs_connections import connect_key
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_grafana_cloudwatch_connections import connect_prometheus, native_group
from tests.test_grafana_prometheus_connections import console, native_workspace
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.TIMESTREAM, None, {})
    )


def native_table(region="us-east-1", database="application.data", table="cpu-load"):
    return {
        "database_arn": f"arn:aws:timestream:{region}:123456789012:database/{database}",
        "database_name": database,
        "region": region,
        "table_name": table,
    }


def evaluate(tmp_path, expression, tables):
    replacements = {
        "var.timestream_tables": json.dumps(tables),
        "var.prometheus_workspaces": json.dumps({"metrics": native_workspace()}),
        "var.cloudwatch_log_groups": json.dumps({"logs": native_group(encrypted=True)}),
        "data.aws_partition.grafana_sources.partition": '"aws"',
        "data.aws_partition.grafana_sources.dns_suffix": '"amazonaws.com"',
        "data.aws_caller_identity.grafana_sources.account_id": '"123456789012"',
    }
    for name, value in replacements.items():
        expression = expression.replace(name, value)
    (tmp_path / "payload.tf").write_text(f"locals {{\n  payload = {expression}\n}}\n")
    return json.loads(json.loads(console(tmp_path, "jsonencode(local.payload)")))


def connect_other_sources(payload):
    connect_prometheus(payload)
    template = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.CLOUDWATCH, None, {})
    )
    payload["resources"].append(dict(template["resources"][1], name="logs", id="logs"))
    payload["connections"].append(
        dict(template["connections"][0], target="logs", target_id="logs")
    )
    connect_key(payload, "logs")


def test_native_database_metadata_and_selected_tables_flow_into_workspace_owned_role():
    tree = generate(architecture())
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 3
    workspace = resources(tree, "aws_grafana_workspace")[0]
    assert workspace["role_arn"] == "${aws_iam_role.source-resource_data_sources.arn}"
    assert workspace["depends_on"] == [
        "${aws_iam_role_policy.source-resource_data_sources}"
    ]
    main = file_with(tree, "/environments/dev/main.tf")
    for output in ["database_arn", "database_name", "database_region"]:
        assert f"module.target-resource.{output}" in main
    assert 'table_name = "application_data"' in main
    target = file_with(tree, "/target-resource/outputs.tf")
    assert 'split(":", aws_timestreamwrite_database.target-resource.arn)[3]' in target
    assert "source-resource" not in target
    source = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "timestream_data_sources"' in source
    assert "aws_iam_role_policy.source-resource_data_sources" in source
    assert not resources(tree, "aws_timestreamwrite_table")
    assert not any(path.endswith("/iam.tf") for path in tree)


@given(
    bindings=st.lists(
        st.tuples(
            resource_name_st, st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True)
        ),
        min_size=1,
        max_size=6,
        unique=True,
    ),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_selected_tables_share_native_databases_and_one_order_independent_role(
    bindings, duplicate
):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in sorted({name for name, _ in bindings}):
        payload["resources"].append(
            dict(deepcopy(target), name=f"data-{name}", id=name)
        )
    for name, table in bindings:
        payload["connections"].append(
            dict(
                connection,
                target=f"data-{name}",
                target_id=name,
                connection_config={"table_name": table},
            )
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_timestreamwrite_database")) == len(
        {name for name, _ in bindings}
    )
    main = file_with(tree, "/environments/dev/main.tf")
    for name, table in bindings:
        assert f'"data-{name}:{table}" = ' in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


def test_multiple_tables_and_distinct_node_names_preserve_independent_bindings():
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in ["data-one", "data_one"]:
        payload["resources"].append(dict(deepcopy(target), name=name, id=name))
        for table in ["cpu.load", "cpu_load"]:
            payload["connections"].append(
                dict(
                    connection,
                    target=name,
                    target_id=name,
                    connection_config={"table_name": table},
                )
            )
    main = file_with(generate(payload), "/environments/dev/main.tf")
    for name in ["data-one", "data_one"]:
        for table in ["cpu.load", "cpu_load"]:
            assert f'"{name}:{table}" = ' in main


@pytest.mark.parametrize(
    "selector", [None, "", "*", "cpu*", "cpu?", "db/table", "ab", "a" * 257]
)
def test_missing_or_unscoped_table_selectors_are_rejected(selector):
    payload = architecture()
    payload["connections"][0]["connection_config"] = (
        {} if selector is None else {"table_name": selector}
    )
    with pytest.raises(InvalidConnectionConfigError, match="table_name"):
        generate(payload)


def test_all_supported_data_sources_share_one_complete_role_in_any_order():
    payload = architecture()
    connect_other_sources(payload)
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 10
    for action in [
        "timestream:Select",
        "aps:QueryMetrics",
        "logs:StartQuery",
        "kms:Decrypt",
    ]:
        assert action in policy["policy"]
    payload["connections"].reverse()
    assert generate(payload) == tree
    source = file_with(tree, "/source-resource/outputs.tf")
    for name in ["timestream", "prometheus", "cloudwatch"]:
        assert f'output "{name}_data_sources"' in source


def test_shared_database_gives_each_grafana_an_independent_role():
    payload = architecture()
    payload["resources"].append(
        dict(deepcopy(payload["resources"][0]), name="other", id="other")
    )
    payload["connections"].append(
        dict(payload["connections"][0], source="other", source_id="other")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 2
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    assert len(resources(tree, "aws_timestreamwrite_database")) == 1


def test_preview_reports_external_tables_discovery_cancellation_and_eligibility():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    messages = "\n".join(item.message for item in preview.issues)
    for text in [
        "provisioned separately",
        "CancelQuery",
        "SELECT 1",
        "eligible existing account",
        "encryption-key",
    ]:
        assert text in messages
    assert not preview.iam
    assert {item.module for item in preview.resources} == {"source-resource"}


def test_catalog_reuses_required_table_schema_and_native_cross_region_references():
    spec = resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.TIMESTREAM, None, {})
    assert spec.config_model is TimestreamTableAccessConfig
    assert spec.connection_type == "queries" and spec.region_policy == "cross-region"
    payload = architecture()
    payload["resources"][1]["provider_region"] = "eu-west-1"
    main = file_with(generate(payload), "/environments/dev/main.tf")
    assert "aws.eu_west_1" in main
    assert "module.target-resource.database_region" in main


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("same", [True, True, True]),
        ("cross_region", [True, True, True]),
        ("cross_account", [True, False, True]),
        ("cross_partition", [True, False, True]),
        ("wrong_service", [False, True, True]),
        ("invalid_arn", [False, False, False]),
        ("wrong_name", [True, True, False]),
        ("wrong_region", [True, True, False]),
        ("table_arn", [False, True, True]),
        ("wildcard_table", [False, True, True]),
        ("wildcard_database", [False, True, True]),
        ("empty", [False, True, True]),
    ],
)
def test_native_guards_reject_identity_mismatches_and_runtime_wildcards(
    tmp_path, mode, expected
):
    table = native_table()
    if mode == "cross_region":
        table = native_table(region="eu-west-1")
    elif mode == "cross_account":
        table["database_arn"] = table["database_arn"].replace(
            "123456789012", "999999999999"
        )
    elif mode == "cross_partition":
        table["database_arn"] = table["database_arn"].replace(
            "arn:aws:", "arn:aws-us-gov:"
        )
    elif mode == "wrong_service":
        table["database_arn"] = table["database_arn"].replace(":timestream:", ":s3:")
    elif mode == "invalid_arn":
        table["database_arn"] = "invalid"
    elif mode == "wrong_name":
        table["database_name"] = "another"
    elif mode == "wrong_region":
        table["region"] = "eu-west-1"
    elif mode == "table_arn":
        table["database_arn"] += "/table/cpu-load"
    elif mode == "wildcard_table":
        table["table_name"] = "cpu*"
    elif mode == "wildcard_database":
        table["database_arn"] = table["database_arn"].replace(
            "application.data", "application*"
        )
        table["database_name"] = "application*"
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in timestream_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(
            tmp_path, expression, {} if mode == "empty" else {"data:cpu-load": table}
        )
        == expected
    )


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
def test_serialized_policy_scopes_records_and_metadata_separately_from_regional_apis(
    tmp_path, mixed
):
    payload = architecture()
    if mixed:
        connect_other_sources(payload)
    text = file_with(generate(payload), "/source-resource/data_source_role.tf")
    expression = re.search(
        r"\n  policy = (jsonencode\(.*?\))\n  lifecycle", text, re.S
    ).group(1)
    first = native_table()
    second = native_table(table="memory")
    remote = native_table(region="eu-west-1", database="remote")
    tables = {"data:cpu-load": first, "data:memory": second, "remote:cpu-load": remote}
    policy = json.loads(evaluate(tmp_path, expression, tables))
    statements = policy["Statement"]
    assert all(isinstance(item, dict) for item in statements)
    by_sid = {item.get("Sid"): item for item in statements}
    queries = by_sid["TimestreamTableQueries"]
    assert set(queries["Action"]) == {
        "timestream:Select",
        "timestream:DescribeTable",
        "timestream:ListMeasures",
    }
    assert queries["Resource"] == [
        f"{table['database_arn']}/table/{table['table_name']}"
        for table in tables.values()
    ]
    metadata = by_sid["TimestreamDatabaseMetadata"]
    assert set(metadata["Action"]) == {
        "timestream:DescribeDatabase",
        "timestream:ListTables",
    }
    assert metadata["Resource"] == [first["database_arn"], remote["database_arn"]]
    regional = by_sid["TimestreamRegionalDiscovery"]
    assert regional["Resource"] == "*"
    assert set(regional["Action"]) == {
        "timestream:DescribeEndpoints",
        "timestream:ListDatabases",
        "timestream:SelectValues",
        "timestream:CancelQuery",
    }
    assert regional["Condition"] == {
        "StringEquals": {"aws:RequestedRegion": ["us-east-1", "eu-west-1"]}
    }
    actions = {
        action
        for item in statements
        for action in (
            item["Action"] if isinstance(item["Action"], list) else [item["Action"]]
        )
    }
    assert (
        not {
            "timestream:WriteRecords",
            "timestream:Unload",
            "timestream:CreateTable",
            "timestream:CreateScheduledQuery",
        }
        & actions
    )
    assert ("aps:QueryMetrics" in actions) is mixed
    assert ("logs:StartQuery" in actions) is mixed
    assert ("kms:Decrypt" in actions) is mixed


@needs_terraform
@pytest.mark.parametrize(
    "database,table", [("application.data", "cpu-load"), ("select", "order")]
)
def test_exported_payloads_quote_sql_defaults_and_use_native_table_uids(
    tmp_path, database, table
):
    native = native_table(region="eu-west-1", database=database, table=table)
    expression = str(timestream_data_sources_expression())
    payloads = evaluate(tmp_path, expression, {f"data:{table}": native})
    arn = f"{native['database_arn']}/table/{table}"
    assert payloads == {
        f"data:{table}": {
            "name": f"data:{table}",
            "uid": "ts-" + hashlib.sha256(arn.encode()).hexdigest()[:16],
            "type": "grafana-timestream-datasource",
            "access": "proxy",
            "jsonData": {
                "authType": "default",
                "defaultRegion": "eu-west-1",
                "defaultDatabase": json.dumps(database),
                "defaultTable": json.dumps(table),
            },
        }
    }
    renamed = evaluate(tmp_path, expression, {f"renamed:{table}": native})
    assert renamed[f"renamed:{table}"]["uid"] == payloads[f"data:{table}"]["uid"]


@needs_terraform
@pytest.mark.parametrize("length", [188, 189, 256])
def test_long_table_names_preserve_selectors_and_get_bounded_distinct_display_names(
    tmp_path, length
):
    tables = {f"d:{'a' * length}": native_table(table="a" * length)}
    tables[f"d:{'a' * (length - 1)}b"] = native_table(table="a" * (length - 1) + "b")
    payload = architecture()
    payload["connections"][0]["connection_config"]["table_name"] = "a" * length
    generate(payload)
    payloads = evaluate(tmp_path, str(timestream_data_sources_expression()), tables)
    assert len({item["name"] for item in payloads.values()}) == 2
    assert len({item["uid"] for item in payloads.values()}) == 2
    for binding, native in tables.items():
        item = payloads[binding]
        assert len(item["name"]) <= 190
        assert item["jsonData"]["defaultTable"] == json.dumps(native["table_name"])
        if len(binding) <= 190:
            assert item["name"] == binding
        else:
            assert item["name"].startswith(binding[:173])
            assert item["name"].endswith(
                hashlib.sha256(binding.encode()).hexdigest()[:16]
            )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize("mode", ["plain", "cross_region", "multiple_tables", "mixed"])
def test_generated_projects_validate_and_preserve_shared_role_dependency_graph(
    tmp_path, mode
):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "multiple_tables":
        payload["connections"].append(
            dict(payload["connections"][0], connection_config={"table_name": "memory"})
        )
    elif mode == "mixed":
        connect_other_sources(payload)
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
