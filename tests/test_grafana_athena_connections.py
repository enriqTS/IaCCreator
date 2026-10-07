"""Athena Grafana bindings scope workgroups, Glue tables, and result objects."""

import hashlib
import json
import re
from copy import deepcopy
from fnmatch import fnmatchcase

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_athena import (
    athena_data_sources_expression,
    athena_scope_preconditions,
)
from app.models.connection_configs.grafana_athena import GrafanaAthenaConfig
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
from tests.test_grafana_opensearch_connections import connect_all_sources, native_domain
from tests.test_grafana_prometheus_connections import console, native_workspace
from tests.test_grafana_timestream_connections import native_table
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.ATHENA, None, {})
    )


def native_workgroup(
    region="us-east-1",
    name="application",
    database="application",
    table="records",
    location="s3://query-results/grafana/results/",
):
    return {
        "arn": f"arn:aws:athena:{region}:123456789012:workgroup/{name}",
        "workgroup_name": name,
        "region": region,
        "database_name": database,
        "table_name": table,
        "output_location": location,
        "enforce_configuration": True,
    }


def evaluate(tmp_path, expression, tables, partition="aws"):
    replacements = {
        "var.athena_tables": json.dumps(tables),
        "var.prometheus_workspaces": json.dumps({"metrics": native_workspace()}),
        "var.cloudwatch_log_groups": json.dumps({"logs": native_group(encrypted=True)}),
        "var.timestream_tables": json.dumps({"time:cpu": native_table()}),
        "var.opensearch_sources": json.dumps({"search:records": native_domain()}),
        "data.aws_partition.grafana_sources.partition": json.dumps(partition),
        "data.aws_partition.grafana_sources.dns_suffix": '"amazonaws.com"',
        "data.aws_caller_identity.grafana_sources.account_id": '"123456789012"',
    }
    for name, value in replacements.items():
        expression = expression.replace(name, value)
    (tmp_path / "payload.tf").write_text(f"locals {{\n  payload = {expression}\n}}\n")
    return json.loads(json.loads(console(tmp_path, "jsonencode(local.payload)")))


def connect_results(payload, prefix="grafana/results", target="target-resource"):
    template = connection_architecture(
        resolve_spec(ServiceType.ATHENA, ServiceType.S3, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][1], name="results", id="results")
    )
    resource = next(item for item in payload["resources"] if item["name"] == target)
    resource["config"].pop("output_location", None)
    payload["connections"].append(
        dict(
            template["connections"][0],
            source=target,
            source_id=resource["id"],
            target="results",
            target_id="results",
            connection_config={"prefix": prefix},
        )
    )


def connect_every_source(payload):
    connect_all_sources(payload)
    template = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.OPENSEARCH, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][1], name="search", id="search")
    )
    payload["connections"].append(
        dict(template["connections"][0], target="search", target_id="search")
    )


def test_native_workgroup_outputs_and_shared_role_preserve_module_ownership():
    tree = generate(architecture())
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 4
    main = file_with(tree, "/environments/dev/main.tf")
    for output in [
        "workgroup_arn",
        "workgroup_name",
        "grafana_workgroup_region",
        "grafana_result_location",
        "grafana_enforce_configuration",
    ]:
        assert f"module.target-resource.{output}" in main
    target = file_with(tree, "/target-resource/outputs.tf")
    assert 'split(":", aws_athena_workgroup.target-resource.arn)[3]' in target
    assert ".configuration[0].result_configuration[0].output_location" in target
    assert "source-resource" not in target
    source = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "athena_data_sources"' in source
    assert "aws_iam_role_policy.source-resource_data_sources" in source
    assert not resources(tree, "aws_glue_catalog_table")
    assert not any(path.endswith("/iam.tf") for path in tree)


@given(
    bindings=st.lists(
        st.tuples(
            resource_name_st,
            st.from_regex(r"[a-z][a-z0-9_]{2,12}", fullmatch=True),
            st.from_regex(r"[a-z][a-z0-9_]{2,12}", fullmatch=True),
        ),
        min_size=1,
        max_size=6,
        unique=True,
    ),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_tables_and_workgroups_share_one_order_independent_role(bindings, duplicate):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in sorted({name for name, _, _ in bindings}):
        payload["resources"].append(
            dict(deepcopy(target), name=f"data-{name}", id=name)
        )
    for name, database, table in bindings:
        payload["connections"].append(
            dict(
                connection,
                target=f"data-{name}",
                target_id=name,
                connection_config={"database_name": database, "table_name": table},
            )
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_athena_workgroup")) == len(
        {name for name, _, _ in bindings}
    )
    main = file_with(tree, "/environments/dev/main.tf")
    for name, database, table in bindings:
        assert f'"data-{name}:{database}:{table}" = ' in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


@pytest.mark.parametrize("field", ["database_name", "table_name"])
@pytest.mark.parametrize(
    "value", [None, "", "*", "logs*", "db/table", "UPPER", "${var.table}", "a" * 256]
)
def test_missing_or_unscoped_table_selectors_are_rejected(field, value):
    payload = architecture()
    if value is None:
        payload["connections"][0]["connection_config"].pop(field)
    else:
        payload["connections"][0]["connection_config"][field] = value
    with pytest.raises(InvalidConnectionConfigError, match=field):
        generate(payload)


@pytest.mark.parametrize(
    "location",
    [
        None,
        "",
        "s3://query-results/",
        "s3://query-results/results",
        "s3://query-results/results*/",
        "s3://query-results/results?/",
        "s3://query-results/${var.prefix}/",
        "s3://query-results/results//",
        "https://query-results/results/",
        "s3://query-results/../",
    ],
)
def test_missing_or_unsafe_result_locations_are_rejected(location):
    payload = architecture()
    payload["resources"][1]["config"]["output_location"] = location
    with pytest.raises(InvalidConnectionConfigError, match="S3 result prefix"):
        generate(payload)


def test_unenforced_workgroup_results_are_rejected_even_with_managed_bucket():
    payload = architecture()
    payload["resources"][1]["config"]["enforce_workgroup_configuration"] = False
    connect_results(payload)
    with pytest.raises(InvalidConnectionConfigError, match="enforced workgroup"):
        generate(payload)


@pytest.mark.parametrize("prefix", ["", ".", ".."])
def test_managed_result_locations_need_a_safe_nonempty_prefix(prefix):
    payload = architecture()
    connect_results(payload, prefix)
    with pytest.raises(InvalidConnectionConfigError, match="S3 result prefix"):
        generate(payload)


def test_managed_results_override_external_location_without_connection_order_dependencies():
    payload = architecture()
    connect_results(payload)
    payload["resources"][1]["config"]["output_location"] = "s3://external/"
    tree = generate(payload)
    main = file_with(tree, "/environments/dev/main.tf")
    assert (
        'format("s3://%s/%s", module.results.bucket_name, "grafana/results/")' in main
    )
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    payload["connections"].append(
        dict(payload["connections"][0], connection_config={"prefix": "other"})
    )
    with pytest.raises(
        InvalidConnectionConfigError, match="one managed S3 location|S3 result prefix"
    ):
        generate(payload)


def test_all_five_data_sources_share_one_role_and_independent_workspaces_get_separate_roles():
    payload = architecture()
    connect_every_source(payload)
    tree = generate(payload)
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(policy["lifecycle"][0]["precondition"]) == 18
    for action in [
        "athena:StartQueryExecution",
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
    assert len(resources(tree, "aws_athena_workgroup")) == 1


def test_preview_describes_query_and_result_scope_and_external_data_permissions():
    spec = resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.ATHENA, None, {})
    assert spec.config_model is GrafanaAthenaConfig
    assert spec.connection_type == "queries" and spec.region_policy == "cross-region"
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    messages = "\n".join(item.message for item in preview.issues)
    for text in [
        "other users' queries",
        "enforced S3 prefix",
        "bucket listings",
        "SELECT",
        "Dataset S3 access",
        "KMS",
        "Lake Formation",
        "compatible Athena plugin",
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
        ("cross_account", [True, False, True, True]),
        ("cross_partition", [True, False, True, True]),
        ("invalid_arn", [False, False, False, True]),
        ("wrong_region", [True, True, False, True]),
        ("wrong_name", [True, True, False, True]),
        ("wildcard_table", [False, True, True, True]),
        ("wildcard_database", [False, True, True, True]),
        ("unenforced", [True, True, True, False]),
        ("bucket_root", [True, True, True, False]),
        ("wildcard_prefix", [True, True, True, False]),
        ("no_trailing_slash", [True, True, True, False]),
        ("empty", [False, True, True, True]),
    ],
)
def test_native_guards_reject_workgroup_and_result_scope_mismatches(
    tmp_path, mode, expected
):
    native = native_workgroup()
    if mode == "cross_region":
        native = native_workgroup(region="eu-west-1")
    elif mode == "cross_account":
        native["arn"] = native["arn"].replace("123456789012", "999999999999")
    elif mode == "cross_partition":
        native["arn"] = native["arn"].replace("arn:aws:", "arn:aws-cn:")
    elif mode == "invalid_arn":
        native["arn"] = "invalid"
    elif mode == "wrong_region":
        native["region"] = "eu-west-1"
    elif mode == "wrong_name":
        native["workgroup_name"] = "another"
    elif mode == "wildcard_table":
        native["table_name"] = "records*"
    elif mode == "wildcard_database":
        native["database_name"] = "app*"
    elif mode == "unenforced":
        native["enforce_configuration"] = False
    elif mode == "bucket_root":
        native["output_location"] = "s3://query-results/"
    elif mode == "wildcard_prefix":
        native["output_location"] = "s3://query-results/results*/"
    elif mode == "no_trailing_slash":
        native["output_location"] = "s3://query-results/results"
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in athena_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(
            tmp_path,
            expression,
            {} if mode == "empty" else {"data:app:records": native},
        )
        == expected
    )


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
@pytest.mark.parametrize("partition", ["aws", "aws-cn"])
def test_serialized_iam_uses_exact_tables_workgroups_and_result_prefixes(
    tmp_path, mixed, partition
):
    payload = architecture()
    if mixed:
        connect_every_source(payload)
    text = file_with(generate(payload), "/source-resource/data_source_role.tf")
    expression = re.search(
        r"\n  policy = (jsonencode\(.*?\))\n  lifecycle", text, re.S
    ).group(1)
    first = native_workgroup()
    second = native_workgroup(table="events")
    remote = native_workgroup(
        region="eu-west-1",
        name="remote",
        database="analytics",
        location="s3://remote-results/dashboard/",
    )
    tables = {
        "data:app:records": first,
        "data:app:events": second,
        "remote:analytics:records": remote,
    }
    for native in tables.values():
        native["arn"] = native["arn"].replace("arn:aws:", f"arn:{partition}:")
    policy = json.loads(evaluate(tmp_path, expression, tables, partition))
    assert all(isinstance(item, dict) for item in policy["Statement"])
    by_sid = {item.get("Sid"): item for item in policy["Statement"]}
    assert by_sid["AthenaWorkgroupQueries"]["Resource"] == [first["arn"], remote["arn"]]
    assert set(by_sid["AthenaWorkgroupQueries"]["Action"]) == {
        "athena:GetWorkGroup",
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution",
    }
    assert by_sid["AthenaCatalogMetadata"]["Resource"] == [
        f"arn:{partition}:athena:{region}:123456789012:datacatalog/AwsDataCatalog"
        for region in ["us-east-1", "eu-west-1"]
    ]
    glue = by_sid["AthenaGlueMetadata"]
    assert len(glue["Resource"]) == 7
    assert set(glue["Resource"]) == {
        f"arn:{partition}:glue:us-east-1:123456789012:catalog",
        f"arn:{partition}:glue:us-east-1:123456789012:database/application",
        f"arn:{partition}:glue:us-east-1:123456789012:table/application/records",
        f"arn:{partition}:glue:us-east-1:123456789012:table/application/events",
        f"arn:{partition}:glue:eu-west-1:123456789012:catalog",
        f"arn:{partition}:glue:eu-west-1:123456789012:database/analytics",
        f"arn:{partition}:glue:eu-west-1:123456789012:table/analytics/records",
    }
    assert not any("*" in arn for arn in glue["Resource"])
    assert by_sid["AthenaRegionalDiscovery"]["Condition"] == {
        "StringEquals": {"aws:RequestedRegion": ["us-east-1", "eu-west-1"]}
    }
    assert by_sid["AthenaResultBucketMetadata"]["Resource"] == [
        f"arn:{partition}:s3:::query-results",
        f"arn:{partition}:s3:::remote-results",
    ]
    objects = by_sid["AthenaResultObjects"]
    assert objects["Resource"] == [
        f"arn:{partition}:s3:::query-results/grafana/results/*",
        f"arn:{partition}:s3:::remote-results/dashboard/*",
    ]
    assert set(objects["Action"]) == {
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts",
    }
    for key, allowed in [
        ("grafana/results/query.csv", True),
        ("grafana/results/tables/query.csv", True),
        ("grafana/results-other/query.csv", False),
        ("dataset/records.parquet", False),
        ("other/query.csv", False),
    ]:
        assert (
            any(
                fnmatchcase(f"arn:{partition}:s3:::query-results/{key}", arn)
                for arn in objects["Resource"]
            )
            is allowed
        )
    actions = {
        action
        for item in policy["Statement"]
        for action in (
            item["Action"] if isinstance(item["Action"], list) else [item["Action"]]
        )
    }
    assert (
        not {
            "s3:DeleteObject",
            "glue:CreateTable",
            "glue:UpdateTable",
            "glue:DeleteTable",
            "athena:CreateWorkGroup",
            "athena:UpdateWorkGroup",
            "athena:ListQueryExecutions",
            "lambda:InvokeFunction",
            "lakeformation:GetDataAccess",
        }
        & actions
    )
    assert ("OpenSearchMultiSearch" in by_sid) is mixed


@needs_terraform
def test_payloads_group_tables_by_workgroup_database_and_keep_native_identity(tmp_path):
    first = native_workgroup(region="eu-west-1")
    tables = {
        "data:application:records": first,
        "data:application:events": dict(first, table_name="events"),
        "data:analytics:events": dict(
            first, database_name="analytics", table_name="events"
        ),
    }
    expression = str(athena_data_sources_expression())
    payloads = evaluate(tmp_path, expression, tables)
    assert set(payloads) == {"data:application", "data:analytics"}
    for binding, item in payloads.items():
        database = binding.split(":")[1]
        assert item == {
            "name": binding,
            "uid": "at-"
            + hashlib.sha256(
                f"{first['arn']}/database/{database}".encode()
            ).hexdigest()[:16],
            "type": "grafana-athena-datasource",
            "access": "proxy",
            "jsonData": {
                "authType": "default",
                "defaultRegion": "eu-west-1",
                "catalog": "AwsDataCatalog",
                "database": database,
                "workgroup": "application",
                "outputLocation": first["output_location"],
                "resultReuseEnabled": False,
            },
        }
    renamed = evaluate(tmp_path, expression, {"renamed:application:records": first})
    assert renamed["renamed:application"]["uid"] == payloads["data:application"]["uid"]


@needs_terraform
@pytest.mark.parametrize("length", [188, 189, 255])
def test_full_length_database_names_keep_selectors_and_bounded_unique_display_names(
    tmp_path, length
):
    tables = {
        f"d:{'a' * length}:records": native_workgroup(database="a" * length),
        f"d:{'a' * (length - 1)}b:records": native_workgroup(
            database="a" * (length - 1) + "b"
        ),
    }
    payload = architecture()
    payload["connections"][0]["connection_config"]["database_name"] = "a" * length
    generate(payload)
    payloads = evaluate(tmp_path, str(athena_data_sources_expression()), tables)
    assert len({item["name"] for item in payloads.values()}) == 2
    assert len({item["uid"] for item in payloads.values()}) == 2
    for binding, item in payloads.items():
        assert len(item["name"]) <= 190
        assert item["jsonData"]["database"] == binding.split(":")[1]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode", ["plain", "cross_region", "multiple_tables", "managed_results", "mixed"]
)
def test_generated_projects_validate_and_have_acyclic_shared_role_graphs(
    tmp_path, mode
):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "multiple_tables":
        payload["connections"].append(
            dict(
                payload["connections"][0],
                connection_config={
                    "database_name": "application",
                    "table_name": "events",
                },
            )
        )
    elif mode == "managed_results":
        connect_results(payload)
    elif mode == "mixed":
        connect_every_source(payload)
        connect_results(payload)
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
