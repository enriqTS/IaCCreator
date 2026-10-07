"""X-Ray defaults preserve native groups while disclosing regional read access."""

import hashlib
import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_xray import (
    xray_data_sources_expression,
    xray_query_defaults_expression,
    xray_scope_preconditions,
)
from app.models.connection_configs.configs import EmptyConnectionConfig
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
from tests.test_grafana_redshift_connections import (
    connect_all_six_sources,
    native_cluster,
)
from tests.test_grafana_redshift_connections import (
    evaluate as evaluate_redshift,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.X_RAY, None, {})
    )


def native_group(region="us-east-1", name="Checkout", insights=False):
    return {
        "arn": f"arn:aws:xray:{region}:123456789012:group/{name}/TNGX7SW5U6QY36T4ZMOUA3HVLBYCZTWDIOOXY3CJAXTHSS3YCWUA",
        "name": name,
        "region": region,
        "filter_expression": 'service("checkout") { fault = true }',
        "insights_enabled": insights,
    }


def evaluate(tmp_path, expression, groups, partition="aws"):
    return evaluate_redshift(
        tmp_path,
        expression.replace(
            "var.xray_groups",
            json.dumps(groups).replace("${", "$${").replace("%{", "%%{"),
        ),
        {"warehouse:application:grafana_reader": native_cluster()},
        partition,
    )


def connect_prior_sources(payload):
    connect_all_six_sources(payload)
    template = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.REDSHIFT, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][1], name="warehouse", id="warehouse")
    )
    payload["connections"].append(
        dict(template["connections"][0], target="warehouse", target_id="warehouse")
    )


def test_native_group_metadata_flows_into_one_workspace_owned_role():
    tree = generate(architecture())
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert len(resources(tree, "aws_xray_group")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 3
    main = file_with(tree, "/environments/dev/main.tf")
    for output in (
        "group_arn",
        "group_name",
        "grafana_group_region",
        "grafana_group_filter",
        "grafana_group_insights_enabled",
    ):
        assert f"module.target-resource.{output}" in main
    target = file_with(tree, "/target-resource/outputs.tf")
    assert 'split(":", aws_xray_group.target-resource.arn)[3]' in target
    assert ".filter_expression" in target
    assert ".insights_configuration[0].insights_enabled" in target
    assert "source-resource" not in target
    outputs = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "xray_data_sources"' in outputs
    assert 'output "xray_query_defaults"' in outputs
    assert "aws_iam_role_policy.source-resource_data_sources" in outputs
    assert "secureJsonData" not in outputs
    assert not any(path.endswith("/iam.tf") for path in tree)


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_group_bindings_are_order_independent_and_share_one_role(names, duplicate):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in names:
        item = deepcopy(target)
        item.update(name=f"traces-{name}", id=name)
        item["config"]["group_name"] = f"g-{name}"
        payload["resources"].append(item)
        payload["connections"].append(
            dict(connection, target=f"traces-{name}", target_id=name)
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_xray_group")) == len(names)
    main = file_with(tree, "/environments/dev/main.tf")
    for name in names:
        assert f"module.traces-{name}.group_arn" in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "name", ["", "Default", "*", "Group*", "Group/Other", "${var.group}", "a" * 33]
)
def test_unsafe_or_reserved_group_names_are_rejected(name):
    payload = architecture()
    payload["resources"][1]["config"]["group_name"] = name
    with pytest.raises(InvalidConnectionConfigError, match="group_name"):
        generate(payload)


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_blank_group_query_filters_are_rejected(value):
    payload = architecture()
    payload["resources"][1]["config"]["filter_expression"] = value
    with pytest.raises(InvalidConnectionConfigError, match="filter_expression"):
        generate(payload)


def test_unconnected_xray_groups_keep_existing_rendering_and_no_grafana_metadata():
    payload = architecture()
    payload["connections"] = []
    payload["resources"].pop(0)
    payload["resources"][0]["config"]["filter_expression"] = ""
    tree = generate(payload)
    assert len(resources(tree, "aws_xray_group")) == 1
    assert not resources(tree, "aws_iam_role")
    assert "grafana_group" not in file_with(tree, "/target-resource/outputs.tf")


def test_group_can_be_shared_by_workspaces_with_independent_roles():
    payload = architecture()
    payload["resources"].append(
        dict(deepcopy(payload["resources"][0]), name="other", id="other")
    )
    payload["connections"].append(
        dict(payload["connections"][0], source="other", source_id="other")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 2
    assert len(resources(tree, "aws_xray_group")) == 1
    assert "aws_iam_role" not in file_with(tree, "/target-resource/outputs.tf")


def test_organization_workspaces_are_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["account_access_type"] = "ORGANIZATION"
    with pytest.raises(InvalidConnectionConfigError, match="current-account"):
        generate(payload)


def test_preview_explains_regional_access_and_manual_query_application():
    spec = resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.X_RAY, None, {})
    assert spec.config_model is EmptyConnectionConfig
    assert spec.connection_type == "queries" and spec.region_policy == "cross-region"
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    messages = " ".join(issue.message for issue in preview.issues)
    for text in (
        "unrelated traces and groups",
        "not IAM authorization boundaries",
        "unrelated insights",
        "older plugin versions",
        "X-Ray query mode",
        "Application Signals",
        "trace ingestion",
    ):
        assert text in messages
    assert not preview.iam
    assert {item.module for item in preview.resources} == {"source-resource"}


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("same", [True] * 3),
        ("cross_region", [True] * 3),
        ("cross_account", [True, False, True]),
        ("cross_partition", [True, False, True]),
        ("invalid_arn", [False] * 3),
        ("wildcard_arn", [False, True, True]),
        ("wrong_region", [True, True, False]),
        ("wrong_name", [True, True, False]),
        ("empty_filter", [True, True, False]),
        ("reserved_name", [True, True, False]),
        ("empty", [False, True, True]),
    ],
)
def test_native_guards_reject_scope_mismatches(tmp_path, mode, expected):
    group = native_group()
    if mode == "cross_region":
        group = native_group(region="eu-west-1")
    elif mode == "cross_account":
        group["arn"] = group["arn"].replace("123456789012", "999999999999")
    elif mode == "cross_partition":
        group["arn"] = group["arn"].replace("arn:aws:", "arn:aws-cn:")
    elif mode == "invalid_arn":
        group["arn"] = "invalid"
    elif mode == "wildcard_arn":
        group["arn"] = group["arn"].rsplit("/", 1)[0] + "/*"
    elif mode == "wrong_region":
        group["region"] = "eu-west-1"
    elif mode == "wrong_name":
        group["name"] = "Another"
    elif mode == "empty_filter":
        group["filter_expression"] = " \n"
    elif mode == "reserved_name":
        group = native_group(name="Default")
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in xray_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(tmp_path, expression, {} if mode == "empty" else {"traces": group})
        == expected
    )


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
@pytest.mark.parametrize("insights", [False, True])
def test_serialized_iam_scopes_trace_reads_and_optional_insights_to_native_regions(
    tmp_path, mixed, insights
):
    payload = architecture()
    if mixed:
        connect_prior_sources(payload)
    text = file_with(generate(payload), "/source-resource/data_source_role.tf")
    expression = re.search(
        r"\n  policy = (jsonencode\(.*?\))\n  lifecycle", text, re.S
    ).group(1)
    groups = {
        "traces": native_group(insights=insights),
        "other": native_group(name="Other", insights=insights),
        "remote": native_group(region="eu-west-1"),
    }
    policy = json.loads(evaluate(tmp_path, expression, groups))
    statements = {item["Sid"]: item for item in policy["Statement"] if "Sid" in item}
    traces = statements["XRayTraceReads"]
    assert set(traces["Action"]) == {
        "xray:BatchGetTraces",
        "xray:GetTraceSummaries",
        "xray:GetTraceGraph",
        "xray:GetGroups",
        "xray:GetTimeSeriesServiceStatistics",
        "xray:GetServiceGraph",
    }
    for sid in ("XRayTraceReads", "XRayRegionDiscovery"):
        assert statements[sid]["Resource"] == "*"
        assert set(
            statements[sid]["Condition"]["StringEquals"]["aws:RequestedRegion"]
        ) == {"us-east-1", "eu-west-1"}
    assert ("XRayInsightReads" in statements) is insights
    if insights:
        assert statements["XRayInsightReads"]["Resource"] == "*"
        assert statements["XRayInsightReads"]["Condition"]["StringEquals"][
            "aws:RequestedRegion"
        ] == ["us-east-1"]
        assert set(statements["XRayInsightReads"]["Action"]) == {
            "xray:GetInsightSummaries",
            "xray:GetInsight",
        }
    actions = {
        action for statement in policy["Statement"] for action in statement["Action"]
    }
    forbidden = {
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:CreateGroup",
        "xray:UpdateGroup",
        "xray:PutEncryptionConfig",
        "xray:GetSamplingTargets",
        "xray:StartTraceRetrieval",
        "application-signals:ListServices",
        "oam:ListSinks",
        "sts:AssumeRole",
    }
    assert not forbidden & actions
    if not mixed:
        assert "kms:Decrypt" not in actions
    assert ("RedshiftClusterQueries" in statements) is mixed
    assert ("AthenaWorkgroupQueries" in statements) is mixed


@needs_terraform
@pytest.mark.parametrize("partition", ["aws", "aws-cn"])
def test_sources_group_by_region_and_keep_identity_across_node_and_group_changes(
    tmp_path, partition
):
    groups = {
        "traces": native_group(),
        "other": native_group(name="Other"),
        "remote": native_group(region="eu-west-1"),
    }
    for group in groups.values():
        group["arn"] = group["arn"].replace("arn:aws:", f"arn:{partition}:")
    expression = str(xray_data_sources_expression())
    payloads = evaluate(tmp_path, expression, groups, partition)
    assert set(payloads) == {"us-east-1", "eu-west-1"}
    for region, item in payloads.items():
        assert item == {
            "name": f"X-Ray {region}",
            "uid": "xr-"
            + hashlib.sha256(f"{partition}:123456789012:{region}".encode()).hexdigest()[
                :16
            ],
            "type": "grafana-x-ray-datasource",
            "access": "proxy",
            "jsonData": {"authType": "default", "defaultRegion": region},
        }
    assert (
        evaluate(
            tmp_path,
            expression,
            {"renamed": groups["other"], "remote": groups["remote"]},
            partition,
        )
        == payloads
    )


@needs_terraform
@pytest.mark.parametrize("insights", [False, True])
def test_native_filters_and_group_objects_are_exported_as_query_defaults(
    tmp_path, insights
):
    group = native_group(region="eu-west-1", insights=insights)
    group["filter_expression"] = (
        'service("checkout") { annotation.note = "${literal}" }\nAND responsetime > 5'
    )
    groups = {"traces": group}
    payloads = evaluate(tmp_path, str(xray_data_sources_expression()), groups)
    defaults = evaluate(tmp_path, str(xray_query_defaults_expression()), groups)[
        "traces"
    ]
    assert defaults["datasource_uid"] == payloads["eu-west-1"]["uid"]
    queries = defaults["queries"]
    assert set(queries) == {"trace_summaries", "service_map"} | (
        {"insights"} if insights else set()
    )
    assert queries["trace_summaries"] == {
        "refId": "A",
        "queryMode": "X-Ray",
        "queryType": "getTraceSummaries",
        "region": "eu-west-1",
        "query": group["filter_expression"],
    }
    for name in ("service_map", "insights") if insights else ("service_map",):
        query = queries[name]
        assert query["region"] == "eu-west-1"
        assert query["queryMode"] == "X-Ray"
        assert query["group"] == {
            "GroupARN": group["arn"],
            "GroupName": group["name"],
            "FilterExpression": group["filter_expression"],
        }
    if insights:
        assert queries["insights"]["state"] == "All"


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    ["plain", "cross_region", "multiple_groups", "insights", "shared_group", "mixed"],
)
def test_projects_validate_and_have_acyclic_role_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "multiple_groups":
        other = deepcopy(payload["resources"][1])
        other.update(name="other", id="other", provider_region="eu-west-1")
        other["config"]["group_name"] = "Other"
        payload["resources"].append(other)
        payload["connections"].append(
            dict(payload["connections"][0], target="other", target_id="other")
        )
    elif mode == "insights":
        payload["resources"][1]["config"]["insights_enabled"] = True
    elif mode == "shared_group":
        payload["resources"].append(
            dict(deepcopy(payload["resources"][0]), name="other", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], source="other", source_id="other")
        )
    elif mode == "mixed":
        connect_prior_sources(payload)
        payload["resources"][1]["config"]["insights_enabled"] = True
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
