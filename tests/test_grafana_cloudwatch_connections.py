"""Logs query grants share Grafana roles and preserve native encryption scope."""

import hashlib
import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.generators.grafana_cloudwatch import (
    cloudwatch_data_sources_expression,
    cloudwatch_scope_preconditions,
)
from app.models.connection_configs.configs import EmptyConnectionConfig
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
from tests.test_grafana_prometheus_connections import console, native_workspace
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.CLOUDWATCH, None, {})
    )


def connect_prometheus(payload):
    template = connection_architecture(
        resolve_spec(
            ServiceType.MANAGED_GRAFANA, ServiceType.MANAGED_PROMETHEUS, None, {}
        )
    )
    target = dict(template["resources"][1], name="metrics", id="metrics")
    payload["resources"].append(target)
    payload["connections"].append(
        dict(template["connections"][0], target="metrics", target_id="metrics")
    )


def native_group(region="us-east-1", name="/aws/lambda/application", encrypted=False):
    return {
        "arn": f"arn:aws:logs:{region}:123456789012:log-group:{name}:*",
        "name": name,
        "region": region,
        "kms_key_arn": f"arn:aws:kms:{region}:123456789012:key/log-key"
        if encrypted
        else "",
        "log_group_class": "STANDARD",
    }


def evaluate(tmp_path, expression, groups):
    replacements = {
        "var.cloudwatch_log_groups": json.dumps(groups),
        "var.prometheus_workspaces": json.dumps({"metrics": native_workspace()}),
        "data.aws_partition.grafana_sources.partition": '"aws"',
        "data.aws_partition.grafana_sources.dns_suffix": '"amazonaws.com"',
        "data.aws_caller_identity.grafana_sources.account_id": '"123456789012"',
    }
    for name, value in replacements.items():
        expression = expression.replace(name, value)
    (tmp_path / "payload.tf").write_text(f"locals {{\n  payload = {expression}\n}}\n")
    return json.loads(json.loads(console(tmp_path, "jsonencode(local.payload)")))


def test_role_and_native_log_group_metadata_are_owned_by_their_modules():
    tree = generate(architecture())
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 4
    workspace = resources(tree, "aws_grafana_workspace")[0]
    assert workspace["role_arn"] == "${aws_iam_role.source-resource_data_sources.arn}"
    assert workspace["depends_on"] == [
        "${aws_iam_role_policy.source-resource_data_sources}"
    ]
    main = file_with(tree, "/environments/dev/main.tf")
    for output in [
        "log_group_arn",
        "log_group_name",
        "log_group_region",
        "log_group_kms_key_arn",
        "log_group_class",
    ]:
        assert f"module.target-resource.{output}" in main
    target = file_with(tree, "/target-resource/outputs.tf")
    assert "aws_cloudwatch_log_group.target-resource.kms_key_id == null" in target
    assert 'split(":", aws_cloudwatch_log_group.target-resource.arn)[3]' in target
    assert "source-resource" not in target
    source = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "cloudwatch_data_sources"' in source
    assert "secureJsonData" not in source
    assert "aws_iam_role_policy.source-resource_data_sources" in source
    assert not any("/target-resource/data_source_role.tf" in path for path in tree)
    assert not any(path.endswith("/iam.tf") for path in tree)


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_multiple_groups_share_one_role_with_order_independent_connections(
    names, duplicate
):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in names:
        payload["resources"].append(
            dict(deepcopy(target), name=f"logs-{name}", id=name)
        )
        payload["connections"].append(
            dict(connection, target=f"logs-{name}", target_id=name)
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert len(resources(tree, "aws_cloudwatch_log_group")) == len(names)
    main = file_with(tree, "/environments/dev/main.tf")
    for name in names:
        assert f"module.logs-{name}.log_group_arn" in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


def test_prometheus_and_encrypted_logs_share_one_complete_policy_in_any_order():
    payload = architecture()
    connect_key(payload, "target-resource")
    connect_prometheus(payload)
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 7
    for action in ["aps:QueryMetrics", "logs:StartQuery", "kms:Decrypt"]:
        assert action in policy["policy"]
    assert '"kms:Encrypt"' not in file_with(
        tree, "/source-resource/data_source_role.tf"
    )
    payload["connections"].reverse()
    assert generate(payload) == tree
    output = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "cloudwatch_data_sources"' in output
    assert 'output "prometheus_data_sources"' in output


@pytest.mark.parametrize("mode", ["plain", "external", "managed"])
def test_preview_explains_logs_only_scope_and_external_encryption_requirements(mode):
    payload = architecture()
    if mode == "external":
        payload["resources"][1]["config"]["kms_key_id"] = native_group(encrypted=True)[
            "kms_key_arn"
        ]
    elif mode == "managed":
        connect_key(payload, "target-resource")
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    messages = "\n".join(item.message for item in preview.issues)
    assert "Logs Insights" in messages and "metrics health checks" in messages
    assert "StopQuery can cancel other queries" in messages
    assert ("external KMS key owner" in messages) is (mode == "external")
    assert not preview.iam


def test_cross_region_inputs_and_catalog_are_native_and_typed():
    payload = architecture()
    payload["resources"][1]["provider_region"] = "eu-west-1"
    tree = generate(payload)
    assert "aws.eu_west_1" in file_with(tree, "/environments/dev/main.tf")
    assert "module.target-resource.log_group_region" in file_with(
        tree, "/environments/dev/main.tf"
    )
    spec = resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.CLOUDWATCH, None, {})
    assert spec.connection_type == "queries"
    assert spec.region_policy == "cross-region"
    assert spec.config_model is EmptyConnectionConfig


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("same", [True, True, True, True]),
        ("cross_region", [True, True, True, True]),
        ("cross_account", [True, False, True, True]),
        ("cross_partition", [True, False, True, True]),
        ("wrong_service", [False, True, True, True]),
        ("invalid_arn", [False, False, False, True]),
        ("wrong_region", [True, True, False, True]),
        ("wrong_name", [True, True, False, True]),
        ("delivery_class", [True, True, False, True]),
        ("infrequent_class", [True, True, True, True]),
        ("bare_arn", [True, True, True, True]),
        ("encrypted", [True, True, True, True]),
        ("wrong_key_region", [True, True, True, False]),
        ("key_alias", [True, True, True, False]),
        ("wrong_key_partition", [True, True, True, False]),
        ("empty", [False, True, True, True]),
    ],
)
def test_native_guards_reject_unmodeled_log_and_encryption_scope(
    tmp_path, mode, expected
):
    group = native_group()
    if mode == "cross_region":
        group = native_group(region="eu-west-1", encrypted=True)
    elif mode == "cross_account":
        group["arn"] = group["arn"].replace("123456789012", "999999999999")
    elif mode == "cross_partition":
        group["arn"] = group["arn"].replace("arn:aws:", "arn:aws-us-gov:")
    elif mode == "wrong_service":
        group["arn"] = group["arn"].replace(":logs:", ":sqs:")
    elif mode == "invalid_arn":
        group["arn"] = "invalid"
    elif mode == "wrong_region":
        group["region"] = "eu-west-1"
    elif mode == "wrong_name":
        group["name"] = "another-group"
    elif mode in {"delivery_class", "infrequent_class"}:
        group["log_group_class"] = (
            "DELIVERY" if mode == "delivery_class" else "INFREQUENT_ACCESS"
        )
    elif mode == "bare_arn":
        group["arn"] = group["arn"].removesuffix(":*")
    elif mode in {"encrypted", "wrong_key_region", "key_alias", "wrong_key_partition"}:
        group = native_group(encrypted=True)
        if mode == "wrong_key_region":
            group["kms_key_arn"] = group["kms_key_arn"].replace(
                "us-east-1", "eu-west-1"
            )
        elif mode == "key_alias":
            group["kms_key_arn"] = group["kms_key_arn"].replace(
                "key/log-key", "alias/log-key"
            )
        elif mode == "wrong_key_partition":
            group["kms_key_arn"] = group["kms_key_arn"].replace(
                "arn:aws:", "arn:aws-cn:"
            )
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in cloudwatch_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(tmp_path, expression, {} if mode == "empty" else {"logs": group})
        == expected
    )


@needs_terraform
@pytest.mark.parametrize(
    "encrypted,mixed", [(False, False), (True, False), (True, True)]
)
def test_serialized_policy_is_flat_scoped_and_conditionally_grants_decryption(
    tmp_path, encrypted, mixed
):
    payload = architecture()
    if mixed:
        connect_prometheus(payload)
    tree = generate(payload)
    text = file_with(tree, "/source-resource/data_source_role.tf")
    expression = re.search(
        r"\n  policy = (jsonencode\(.*?\))\n  lifecycle", text, re.S
    ).group(1)
    group = native_group(region="eu-west-1", encrypted=encrypted)
    policy = json.loads(evaluate(tmp_path, expression, {"logs": group}))
    statements = policy["Statement"]
    assert all(isinstance(item, dict) for item in statements)
    by_sid = {item.get("Sid"): item for item in statements}
    arn = group["arn"].removesuffix(":*")
    assert by_sid["CloudWatchLogQueries"]["Resource"] == [arn, arn + ":*"]
    assert by_sid["CloudWatchLogEvents"]["Resource"] == [arn + ":log-stream:*"]
    lifecycle = by_sid["CloudWatchQueryLifecycle"]
    assert lifecycle["Resource"] == "*"
    assert lifecycle["Condition"] == {
        "StringEquals": {"aws:RequestedRegion": ["eu-west-1"]}
    }
    decrypt = [item for item in statements if item["Action"] == ["kms:Decrypt"]]
    assert len(decrypt) == int(encrypted)
    if encrypted:
        assert decrypt[0]["Resource"] == group["kms_key_arn"]
        assert decrypt[0]["Condition"] == {
            "StringEquals": {
                "kms:ViaService": "logs.eu-west-1.amazonaws.com",
                "kms:EncryptionContext:aws:logs:arn": arn,
            }
        }
    prometheus = [item for item in statements if "aps:QueryMetrics" in item["Action"]]
    assert len(prometheus) == int(mixed)
    if mixed:
        assert prometheus[0]["Resource"] == [native_workspace()["arn"]]
    actions = [
        action
        for statement in statements
        for action in (
            statement["Action"]
            if isinstance(statement["Action"], list)
            else [statement["Action"]]
        )
    ]
    assert "cloudwatch:GetMetricData" not in actions
    assert "logs:PutLogEvents" not in actions
    assert "kms:Encrypt" not in actions


@needs_terraform
def test_payloads_group_defaults_by_native_region_and_use_stable_credentials_free_uids(
    tmp_path,
):
    groups = {
        "logs-one": native_group(name="/app/one"),
        "logs_one": native_group(name="/app/two"),
        "remote": native_group(name="/app/remote", region="eu-west-1"),
    }
    expression = str(cloudwatch_data_sources_expression())
    payloads = evaluate(tmp_path, expression, groups)
    assert set(payloads) == {"us-east-1", "eu-west-1"}
    for region, payload in payloads.items():
        assert payload == {
            "name": f"CloudWatch Logs {region}",
            "uid": "cwlogs-"
            + hashlib.sha256(f"123456789012:{region}".encode()).hexdigest()[:16],
            "type": "cloudwatch",
            "access": "proxy",
            "jsonData": {
                "authType": "default",
                "defaultRegion": region,
                "logGroups": [
                    {
                        "arn": group["arn"].removesuffix(":*"),
                        "name": group["name"],
                        "accountId": "123456789012",
                    }
                    for _, group in sorted(groups.items())
                    if group["region"] == region
                ],
            },
        }
    assert payloads == evaluate(
        tmp_path, expression, dict(reversed(list(groups.items())))
    )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode", ["plain", "cross_region", "mixed_encrypted", "cloudtrail_encrypted"]
)
def test_generated_projects_validate_and_have_no_shared_role_cycles(tmp_path, mode):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "mixed_encrypted":
        connect_key(payload, "target-resource")
        connect_prometheus(payload)
    elif mode == "cloudtrail_encrypted":
        connect_key(payload, "target-resource")
        template = connection_architecture(
            resolve_spec(ServiceType.CLOUDTRAIL, ServiceType.CLOUDWATCH, None, {})
        )
        trail = dict(template["resources"][0], name="audit", id="audit")
        trail["config"]["s3_bucket_name"] = "external-audit-bucket"
        payload["resources"].append(trail)
        payload["connections"].append(
            dict(template["connections"][0], source="audit", source_id="audit")
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
