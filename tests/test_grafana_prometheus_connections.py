"""Grafana roles scope queries while exporting native, credential-free data sources."""

import hashlib
import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_data_sources import grafana_workspace_attributes
from app.generators.grafana_prometheus import (
    prometheus_data_sources_expression,
    prometheus_scope_preconditions,
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
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(
            ServiceType.MANAGED_GRAFANA, ServiceType.MANAGED_PROMETHEUS, None, {}
        )
    )


def test_native_workspace_waits_for_scoped_queries_and_trusted_role():
    payload = architecture()
    tree = generate(payload)
    workspace = resources(tree, "aws_grafana_workspace")[0]
    assert workspace["role_arn"] == "${aws_iam_role.source-resource_data_sources.arn}"
    assert workspace["depends_on"] == [
        "${aws_iam_role_policy.source-resource_data_sources}"
    ]
    assert len(workspace["lifecycle"][0]["precondition"]) == 2
    assert 'permission_type = "CUSTOMER_MANAGED"' in file_with(
        tree, "/environments/dev/main.tf"
    )
    assert (
        payload["resources"][0]["config"].get("permission_type", "SERVICE_MANAGED")
        == "SERVICE_MANAGED"
    )
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    role = resources(tree, "aws_iam_role")[0]
    assert role["name_prefix"] == "grafana-data-sources-"
    text = file_with(tree, "/source-resource/data_source_role.tf")
    assert '"grafana.${data.aws_partition.grafana_sources.dns_suffix}"' in text
    assert '"aws:SourceAccount"' in text and '"aws:SourceArn"' in text
    assert ":/workspaces/*" in text
    assert "aws_grafana_workspace." not in text
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 3
    for action in [
        "aps:QueryMetrics",
        "aps:GetLabels",
        "aps:GetSeries",
        "aps:GetMetricMetadata",
    ]:
        assert action in policy["policy"]
    for action in [
        "aps:RemoteWrite",
        "aps:ListWorkspaces",
        "aps:DescribeWorkspace",
        "sts:AssumeRole",
    ]:
        assert action not in policy["policy"]
    assert "workspace.arn" in policy["policy"]
    assert "module." not in text
    assert not any(path.endswith("/iam.tf") for path in tree)
    main = file_with(tree, "/environments/dev/main.tf")
    for output in ["workspace_arn", "prometheus_endpoint", "workspace_region"]:
        assert f"module.target-resource.{output}" in main
    outputs = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "prometheus_data_sources"' in outputs
    assert "grafana-amazonprometheus-datasource" in outputs
    assert 'sigV4AuthType = "default"' in outputs
    assert 'sigv4Service = "aps"' in outputs
    assert (
        "aws_grafana_workspace.source-resource, aws_iam_role_policy.source-resource_data_sources"
        in outputs
    )
    assert "secureJsonData" not in outputs and "sigV4AccessKey" not in outputs


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_multiple_workspaces_share_one_role_and_order_independent_policy(
    names, duplicate
):
    payload = architecture()
    target_template = deepcopy(payload["resources"][1])
    connection_template = deepcopy(payload["connections"][0])
    payload["resources"] = payload["resources"][:1]
    payload["connections"] = []
    for name in names:
        target = deepcopy(target_template)
        target.update(name=f"metrics-{name}", id=f"metrics-{name}")
        payload["resources"].append(target)
        payload["connections"].append(
            dict(connection_template, target=target["name"], target_id=target["id"])
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    main = file_with(tree, "/environments/dev/main.tf")
    for name in names:
        assert f"module.metrics-{name}.workspace_arn" in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


def test_distinct_names_preserve_separate_native_workspaces():
    payload = architecture()
    template = deepcopy(payload["resources"][1])
    payload["resources"] = payload["resources"][:1]
    payload["connections"] = []
    for name in ["metrics-one", "metrics_one"]:
        target = deepcopy(template)
        target.update(name=name, id=name)
        payload["resources"].append(target)
        payload["connections"].append(
            {
                "source": "source-resource",
                "source_id": "src",
                "target": name,
                "target_id": name,
                "connection_type": "queries",
            }
        )
    main = file_with(generate(payload), "/environments/dev/main.tf")
    assert "module.metrics-one.workspace_arn" in main
    assert "module.metrics_one.workspace_arn" in main


def test_shared_prometheus_workspace_gives_each_grafana_its_own_role():
    payload = architecture()
    other = deepcopy(payload["resources"][0])
    other.update(name="other", id="other")
    payload["resources"].append(other)
    payload["connections"].append(
        dict(payload["connections"][0], source="other", source_id="other")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 2
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    assert len(resources(tree, "aws_prometheus_workspace")) == 1
    assert not any("/target-resource/data_source_role.tf" in path for path in tree)


def test_organization_role_chaining_is_rejected_for_generation_and_preview():
    payload = architecture()
    payload["resources"][0]["config"]["account_access_type"] = "ORGANIZATION"
    for operation in (
        generate,
        lambda data: ConnectionPreviewer().preview_all(project(data)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match="current-account"):
            operation(payload)


@pytest.mark.parametrize("permission", ["SERVICE_MANAGED", "CUSTOMER_MANAGED"])
def test_connection_derives_customer_permissions_and_retains_external_source_settings(
    permission,
):
    payload = architecture()
    payload["resources"][0]["config"].update(
        permission_type=permission, data_sources=["CLOUDWATCH"]
    )
    ir = project(payload)
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert {(item.module, item.resource_type) for item in preview.resources} == {
        ("source-resource", "aws_iam_role"),
        ("source-resource", "aws_iam_role_policy"),
    }
    assert not preview.iam
    assert any("data-source API" in issue.message for issue in preview.issues)
    assert any("Other configured" in issue.message for issue in preview.issues)
    tree = generate(payload)
    assert 'permission_type = "CUSTOMER_MANAGED"' in file_with(
        tree, "/environments/dev/main.tf"
    )
    assert '"CLOUDWATCH"' in file_with(tree, "/environments/dev/main.tf")


def test_cross_region_connections_use_the_prometheus_native_signing_region():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "eu-west-1"
    tree = generate(payload)
    main = file_with(tree, "/environments/dev/main.tf")
    assert "aws.eu_west_1" in main
    assert "module.target-resource.workspace_region" in main
    assert "sigV4Region = workspace.region" in file_with(
        tree, "/source-resource/outputs.tf"
    )


def test_unconnected_grafana_keeps_existing_generation():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    workspace = resources(tree, "aws_grafana_workspace")[0]
    assert "role_arn" not in workspace and "lifecycle" not in workspace
    assert "depends_on" not in workspace
    assert 'permission_type = "SERVICE_MANAGED"' in file_with(
        tree, "/environments/dev/main.tf"
    )
    assert not resources(tree, "aws_iam_role")
    assert "prometheus_data_sources" not in "\n".join(tree.values())


def test_catalog_uses_typed_empty_configuration_and_cross_region_policy():
    spec = resolve_spec(
        ServiceType.MANAGED_GRAFANA, ServiceType.MANAGED_PROMETHEUS, None, {}
    )
    assert spec.connection_type == "queries"
    assert spec.config_model is EmptyConnectionConfig
    assert spec.region_policy == "cross-region"
    assert (
        resolve_spec(
            ServiceType.MANAGED_PROMETHEUS, ServiceType.MANAGED_GRAFANA, None, {}
        )
        is None
    )


def console(tmp_path, expression):
    result = subprocess.run(
        ["terraform", "console"],
        input=expression.replace("\n", " "),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def native_workspace(
    region="us-east-1", account="123456789012", partition="aws", suffix="amazonaws.com"
):
    identifier = "ws-12345678-1234-1234-1234-123456789012"
    return {
        "arn": f"arn:{partition}:aps:{region}:{account}:workspace/{identifier}",
        "region": region,
        "endpoint": f"https://aps-workspaces.{region}.{suffix}/workspaces/{identifier}/",
    }


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("same", [True, True, True]),
        ("cross_region", [True, True, True]),
        ("cross_account", [True, False, True]),
        ("cross_partition", [True, False, True]),
        ("wrong_service", [False, True, True]),
        ("wrong_endpoint", [True, True, False]),
        ("wrong_region", [True, True, False]),
        ("invalid_arn", [False, False, False]),
        ("empty", [False, True, True]),
        ("no_trailing_slash", [True, True, True]),
    ],
)
def test_native_guards_reject_unmodeled_scope_and_endpoint_overrides(
    tmp_path, mode, expected
):
    workspace = native_workspace()
    if mode == "cross_region":
        workspace = native_workspace(region="eu-west-1")
    elif mode == "cross_account":
        workspace = native_workspace(account="999999999999")
    elif mode == "cross_partition":
        workspace = native_workspace(partition="aws-us-gov")
    elif mode == "wrong_service":
        workspace["arn"] = workspace["arn"].replace(":aps:", ":sqs:")
    elif mode == "wrong_endpoint":
        workspace["endpoint"] = "https://unrelated.example.com/workspaces/metrics/"
    elif mode == "wrong_region":
        workspace["region"] = "eu-west-1"
    elif mode == "invalid_arn":
        workspace["arn"] = "invalid"
    elif mode == "no_trailing_slash":
        workspace["endpoint"] = workspace["endpoint"].rstrip("/")
    replacements = {
        "var.prometheus_workspaces": json.dumps(
            {} if mode == "empty" else {"metrics": workspace}
        ),
        "data.aws_partition.grafana_sources.partition": '"aws"',
        "data.aws_partition.grafana_sources.dns_suffix": '"amazonaws.com"',
        "data.aws_caller_identity.grafana_sources.account_id": '"123456789012"',
    }
    expressions = [str(item["condition"]) for item in prometheus_scope_preconditions()]
    for key, value in replacements.items():
        expressions = [expression.replace(key, value) for expression in expressions]
    result = console(tmp_path, "[" + ", ".join(expressions) + "]")
    assert re.findall(r"\b(true|false)\b", result) == [
        str(value).lower() for value in expected
    ]


@needs_terraform
@pytest.mark.parametrize(
    "partition,region,suffix",
    [
        ("aws", "us-east-1", "amazonaws.com"),
        ("aws", "eu-west-1", "amazonaws.com"),
        ("aws-cn", "cn-north-1", "amazonaws.com.cn"),
    ],
)
def test_exported_api_payloads_use_actual_workspace_identity_without_credentials(
    tmp_path, partition, region, suffix
):
    workspace = native_workspace(partition=partition, region=region, suffix=suffix)
    expression = str(prometheus_data_sources_expression()).replace(
        "var.prometheus_workspaces", json.dumps({"metrics": workspace})
    )
    (tmp_path / "payload.tf").write_text(f"locals {{\n  payload = {expression}\n}}\n")
    output = json.loads(console(tmp_path, "jsonencode(local.payload)"))
    data_sources = json.loads(output)
    assert data_sources == {
        "metrics": {
            "name": "metrics",
            "uid": "amp-" + hashlib.sha256(workspace["arn"].encode()).hexdigest()[:16],
            "type": "grafana-amazonprometheus-datasource",
            "access": "proxy",
            "url": workspace["endpoint"],
            "jsonData": {
                "httpMethod": "POST",
                "sigV4Auth": True,
                "sigV4AuthType": "default",
                "sigV4Region": region,
                "sigv4Service": "aps",
            },
        }
    }


@needs_terraform
@pytest.mark.parametrize(
    "permission,account,expected",
    [
        ("CUSTOMER_MANAGED", "CURRENT_ACCOUNT", [True, True]),
        ("SERVICE_MANAGED", "CURRENT_ACCOUNT", [False, True]),
        ("CUSTOMER_MANAGED", "ORGANIZATION", [True, False]),
    ],
)
def test_workspace_preconditions_reject_runtime_permission_and_access_overrides(
    tmp_path, permission, account, expected
):
    expressions = [
        str(item["condition"])
        for item in grafana_workspace_attributes("grafana")["lifecycle"]["precondition"]
    ]
    expressions = [
        expression.replace("var.permission_type", json.dumps(permission)).replace(
            "var.account_access_type", json.dumps(account)
        )
        for expression in expressions
    ]
    assert re.findall(
        r"\b(true|false)\b", console(tmp_path, "[" + ", ".join(expressions) + "]")
    ) == [str(value).lower() for value in expected]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize("mode", ["plain", "cross_region", "shared"])
def test_projects_validate_and_have_no_role_dependency_cycles(tmp_path, mode):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "shared":
        other = deepcopy(payload["resources"][1])
        other.update(name="other", id="other")
        payload["resources"].append(other)
        payload["connections"].append(
            dict(payload["connections"][0], target="other", target_id="other")
        )
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
