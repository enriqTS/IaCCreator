"""Build logs retain role identity, scoped permissions, and existing task settings."""

import json
import re
from copy import deepcopy

import hcl2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.codebuild_logs import build_log_preconditions
from app.models.connection_configs.codebuild_logs import CodeBuildLogsConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_eks_prometheus_connections import evaluate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project
from tests.test_secret_connections import architecture as secret_architecture
from tests.test_step_functions_logs_connections import add_key


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.CODEBUILD, ServiceType.CLOUDWATCH, None, {})
    )


def add_logs(payload, source="source-resource", source_id="src"):
    template = architecture()
    payload["resources"].append(
        dict(template["resources"][1], name="build-logs", id="build-logs")
    )
    payload["connections"].append(
        dict(
            template["connections"][0],
            source=source,
            source_id=source_id,
            target="build-logs",
            target_id="build-logs",
        )
    )


def policy_expression(tree):
    return re.search(
        r"  policy = (.*?)\n  lifecycle \{", file_with(tree, "/build_logs.tf"), re.S
    )[1]


def native_values():
    return {
        "var.service_role": "arn:aws:iam::123456789012:role/build/service-role",
        "var.build_logs": {
            "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/build/application",
            "name": "/build/application",
            "log_group_class": "STANDARD",
            "kms_key_arn": "",
            "stream_prefix": "build",
        },
        "data.aws_partition.build_logs.partition": "aws",
        "data.aws_partition.build_logs.dns_suffix": "amazonaws.com",
        "data.aws_region.build_logs.region": "us-east-1",
        "data.aws_caller_identity.build_logs.account_id": "123456789012",
    }


def test_logging_uses_native_destination_and_existing_role_with_exact_identity_checks():
    tree = generate(architecture())
    build = resources(tree, "aws_codebuild_project")[0]
    logging = build["logs_config"][0]["cloudwatch_logs"][0]
    assert {key: logging[key] for key in ("status", "group_name", "stream_name")} == {
        "status": "ENABLED",
        "group_name": "${var.build_logs.name}",
        "stream_name": "${var.build_logs.stream_prefix}",
    }
    assert build["service_role"] == "${var.service_role}"
    assert build["depends_on"] == ["${aws_iam_role_policy.build_logs}"]
    assert len(build["lifecycle"][0]["precondition"]) == 5
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert policy["role"] == "${data.aws_iam_role.build_logs.name}"
    assert policy["name_prefix"] == "build-logs-"
    assert len(policy["lifecycle"][0]["precondition"]) == 6
    assert 'name = element(reverse(split("/", var.service_role)), 0)' in file_with(
        tree, "/build_logs.tf"
    )
    assert not resources(tree, "aws_iam_role")
    assert not resources(tree, "aws_cloudwatch_log_resource_policy")
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    main = file_with(tree, "/environments/dev/main.tf")
    for output in (
        "log_group_arn",
        "log_group_name",
        "log_group_class",
        "log_group_kms_key_arn",
    ):
        assert f"module.target-resource.{output}" in main
    result = ConnectionProcessor().process_all(project(architecture()))
    assert {(item.module, item.filename) for item in result.resources} == {
        ("source-resource", "build_logs.tf")
    }
    assert not result.iam
    assert "module.source-resource" not in file_with(
        tree, "/target-resource/outputs.tf"
    )


@given(prefix=resource_name_st, count=st.integers(1, 4))
@settings(max_examples=20, deadline=None)
def test_prefix_settings_and_duplicate_edges_are_deterministic(prefix, count):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"stream_prefix": prefix}
    payload["connections"] *= count
    tree = generate(payload)
    parsed = hcl2.loads(
        file_with(tree, "/environments/dev/main.tf"),
        serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True),
    )
    assert (
        parsed["module"][0]["source-resource"]["build_logs"]["stream_prefix"] == prefix
    )
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert (
        file_with(tree, "/source-resource/variables.tf").count('variable "build_logs"')
        == 1
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "config",
    [
        {"stream_prefix": ""},
        {"stream_prefix": "*"},
        {"stream_prefix": "a:b"},
        {"stream_prefix": "a" * 129},
        {"stream_prefix": "${secret}"},
        {"stream_prefix": None},
        {"stream_prefix": True},
        {"stream_prefix": 12},
        {"unknown": True},
    ],
)
def test_invalid_prefixes_and_unknown_fields_are_rejected(config):
    with pytest.raises(ValidationError):
        CodeBuildLogsConfig.model_validate(config)
    payload = architecture()
    payload["connections"][0]["connection_config"] = config
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "role",
    [
        None,
        "",
        "service-role",
        "arn:aws:iam::123456789012:user/build",
        "arn:aws:sts::123456789012:assumed-role/build/session",
        "arn:aws:iam::123456789012:role/*",
    ],
)
def test_invalid_service_roles_fail_generation_and_preview(role):
    payload = architecture()
    payload["resources"][0]["config"]["service_role"] = role
    with pytest.raises(InvalidConnectionConfigError, match="external service role ARN"):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("mode", ["two_groups", "prefix"])
def test_conflicting_destinations_or_prefixes_are_rejected(mode):
    payload = architecture()
    edge = deepcopy(payload["connections"][0])
    if mode == "two_groups":
        payload["resources"].append(
            dict(
                deepcopy(payload["resources"][1]), name="other-group", id="other-group"
            )
        )
        edge.update(target="other-group", target_id="other-group")
    else:
        edge["connection_config"] = {"stream_prefix": "other"}
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "key", ["alias/build-logs", "key-id", "arn:aws:kms:us-east-1:123456789012:key/*"]
)
def test_external_encryption_requires_native_key_arns(key):
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = key
    with pytest.raises(InvalidConnectionConfigError, match="external KMS key ARN"):
        generate(payload)
    add_key(payload)
    assert generate(payload)


def test_delivery_class_and_effective_region_mismatches_are_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["log_group_class"] = "DELIVERY"
    with pytest.raises(InvalidConnectionConfigError, match="Infrequent Access"):
        generate(payload)
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    assert generate(payload)


def test_unconnected_projects_keep_existing_logging_behavior():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    build = resources(tree, "aws_codebuild_project")[0]
    assert "logs_config" not in build and "depends_on" not in build
    assert not resources(tree, "aws_iam_role_policy")


def test_logging_preserves_secret_injection_source_and_build_settings():
    payload = secret_architecture(ServiceType.CODEBUILD)
    payload["resources"][0]["config"]["buildspec"] = (
        "version: 0.2\nphases:\n  build:\n    commands:\n      - echo Run build\n"
    )
    payload["connections"][0]["connection_config"] = {"environment_name": "TOKEN"}
    before = resources(generate(payload), "aws_codebuild_project")[0]
    add_logs(payload)
    tree = generate(payload)
    after = resources(tree, "aws_codebuild_project")[0]
    for field in ("source", "environment", "artifacts", "service_role"):
        assert before[field] == after[field]
    assert after["depends_on"] == [
        *before["depends_on"],
        "${aws_iam_role_policy.build_logs}",
    ]
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_preview_reports_external_trust_key_policies_and_build_override_limits():
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = (
        "arn:aws:kms:us-east-1:123456789012:key/external"
    )
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert {item.resource_type for item in preview.resources} == {"aws_iam_role_policy"}
    message = " ".join(item.message for item in preview.issues)
    for text in (
        "external KMS key owner",
        "codebuild.amazonaws.com",
        "iam:GetRole",
        "full role ARN",
        "external key policies",
        "StartBuild",
        "expose secrets",
    ):
        assert text in message


@needs_terraform
@pytest.mark.parametrize("suffix", ["", ":*"])
@pytest.mark.parametrize("encrypted", [False, True])
def test_actual_policy_limits_group_and_stream_permissions_and_conditional_key_access(
    tmp_path, suffix, encrypted
):
    values = native_values()
    group = values["var.build_logs"]["arn"]
    values["var.build_logs"]["arn"] += suffix
    key = "arn:aws:kms:us-east-1:123456789012:key/native-key"
    if encrypted:
        values["var.build_logs"]["kms_key_arn"] = key
    policy = json.loads(
        evaluate(tmp_path, policy_expression(generate(architecture())), values)
    )
    statements = policy["Statement"]
    assert statements[0] == {
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup"],
        "Resource": group,
    }
    assert statements[1] == {
        "Effect": "Allow",
        "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": f"{group}:log-stream:build*",
    }
    assert len(statements) == (4 if encrypted else 2)
    if encrypted:
        crypto, describe = statements[2:]
        assert set(crypto["Action"]) == {
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
        }
        assert crypto["Resource"] == describe["Resource"] == key
        assert crypto["Condition"] == {
            "StringEquals": {
                "kms:ViaService": "logs.us-east-1.amazonaws.com",
                "kms:EncryptionContext:aws:logs:arn": group,
            }
        }
        assert describe["Action"] == ["kms:DescribeKey"]
        assert describe["Condition"] == {
            "StringEquals": {"kms:ViaService": "logs.us-east-1.amazonaws.com"}
        }


@needs_terraform
@pytest.mark.parametrize(
    "index, mutation",
    [
        (0, {"service_role": "arn:aws:iam::999999999999:role/build"}),
        (0, {"service_role": "arn:aws-cn:iam::123456789012:role/build"}),
        (0, {"service_role": "arn:aws:iam::123456789012:role/*"}),
        (1, {"arn": "not-an-arn"}),
        (
            1,
            {"arn": "arn:aws:logs:eu-west-1:123456789012:log-group:/build/application"},
        ),
        (
            1,
            {"arn": "arn:aws:logs:us-east-1:999999999999:log-group:/build/application"},
        ),
        (
            1,
            {
                "arn": "arn:aws-cn:logs:us-east-1:123456789012:log-group:/build/application"
            },
        ),
        (
            1,
            {
                "arn": "arn:aws:logs:us-east-1:123456789012:log-group:app:log-stream:stream"
            },
        ),
        (2, {"name": "/build/other"}),
        (2, {"log_group_class": "DELIVERY"}),
        (3, {"stream_prefix": "*"}),
        (3, {"stream_prefix": ""}),
        (4, {"kms_key_arn": "alias/build"}),
        (4, {"kms_key_arn": "arn:aws:kms:us-east-1:123456789012:key/*"}),
        (4, {"kms_key_arn": "arn:aws:kms:eu-west-1:123456789012:key/native-key"}),
        (4, {"kms_key_arn": "arn:aws-cn:kms:us-east-1:123456789012:key/native-key"}),
    ],
)
def test_native_guards_reject_unsafe_module_overrides(tmp_path, index, mutation):
    values = native_values()
    for key, value in mutation.items():
        if f"var.{key}" in values:
            values[f"var.{key}"] = value
        else:
            values["var.build_logs"][key] = value
    assert (
        evaluate(tmp_path, str(build_log_preconditions()[index]["condition"]), values)
        is False
    )


@needs_terraform
@pytest.mark.parametrize("log_class", ["STANDARD", "INFREQUENT_ACCESS"])
@pytest.mark.parametrize("encrypted", [False, True])
def test_native_guards_accept_supported_logging(tmp_path, log_class, encrypted):
    values = native_values()
    values["var.build_logs"]["log_group_class"] = log_class
    if encrypted:
        values["var.build_logs"]["kms_key_arn"] = (
            "arn:aws:kms:us-east-1:123456789012:key/native-key"
        )
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in build_log_preconditions())
        + "]"
    )
    assert evaluate(tmp_path, expression, values) == [True] * 5


@needs_terraform
@pytest.mark.parametrize("path", ["build/", "other/", ""])
def test_policy_guard_checks_role_path_before_attachment(tmp_path, path):
    tree = generate(architecture())
    policy = resources(tree, "aws_iam_role_policy")[0]
    expression = policy["lifecycle"][0]["precondition"][-1]["condition"][2:-1]
    values = native_values()
    values["data.aws_iam_role.build_logs.arn"] = (
        f"arn:aws:iam::123456789012:role/{path}service-role"
    )
    assert evaluate(tmp_path, expression, values) is (path == "build/")


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "standard",
        "infrequent",
        "duplicate",
        "shared_group",
        "shared_role",
        "managed_key",
        "external_key",
        "mixed",
        "regional",
    ],
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "infrequent":
        payload["resources"][1]["config"]["log_group_class"] = "INFREQUENT_ACCESS"
    elif mode == "duplicate":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode in {"shared_group", "shared_role"}:
        payload["resources"].append(
            dict(
                deepcopy(payload["resources"][0]), name="other-build", id="other-build"
            )
        )
        edge = dict(
            payload["connections"][0], source="other-build", source_id="other-build"
        )
        if mode == "shared_role":
            payload["resources"].append(
                dict(
                    deepcopy(payload["resources"][1]),
                    name="other-logs",
                    id="other-logs",
                )
            )
            edge.update(target="other-logs", target_id="other-logs")
        payload["connections"].append(edge)
    elif mode == "managed_key":
        add_key(payload)
    elif mode == "external_key":
        payload["resources"][1]["config"]["kms_key_id"] = (
            "arn:aws:kms:us-east-1:123456789012:key/12345678-abcd-1234-abcd-123456789012"
        )
    elif mode == "mixed":
        payload = secret_architecture(ServiceType.CODEBUILD)
        add_logs(payload)
        add_key(payload, "build-logs")
        template = connection_architecture(
            resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.CLOUDWATCH, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][0], name="dashboards", id="dashboards")
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="dashboards",
                source_id="dashboards",
                target="build-logs",
                target_id="build-logs",
            )
        )
        template = connection_architecture(
            resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.CODEBUILD, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][0], name="build-trigger", id="build-trigger")
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="build-trigger",
                source_id="build-trigger",
                target="source-resource",
                target_id="src",
            )
        )
    elif mode == "regional":
        for item in payload["resources"]:
            item["provider_region"] = "eu-west-1"
    tree = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == tree
    if mode in {"shared_group", "shared_role"}:
        assert len(resources(tree, "aws_iam_role_policy")) == 2
    if mode == "managed_key":
        assert "CloudWatchLogsEncryption" in file_with(tree, "/key_policy.tf")
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
