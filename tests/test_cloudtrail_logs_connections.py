"""CloudTrail log-delivery roles, destination guards, and audit-policy composition."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.cloudtrail_logs import (
    cloudtrail_log_stream_arn,
    cloudtrail_logs_preconditions,
)
from app.models.connection_configs.configs import EmptyConnectionConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
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
    payload = connection_architecture(
        resolve_spec(ServiceType.CLOUDTRAIL, ServiceType.CLOUDWATCH, None, {})
    )
    payload["resources"][0]["config"]["s3_bucket_name"] = "external-audit-bucket"
    return payload


def connect_key(payload, target, name="key"):
    if not any(item["name"] == name for item in payload["resources"]):
        key = connection_architecture(
            resolve_spec(ServiceType.KMS, ServiceType.CLOUDWATCH, None, {})
        )["resources"][0]
        key.update(name=name, id=name)
        payload["resources"].append(key)
    destination = next(item for item in payload["resources"] if item["name"] == target)
    payload["connections"].append(
        {
            "source": name,
            "source_id": name,
            "target": target,
            "target_id": destination["id"],
            "connection_type": "encrypts",
        }
    )


def connect_bucket(payload):
    template = connection_architecture(
        resolve_spec(ServiceType.CLOUDTRAIL, ServiceType.S3, None, {})
    )
    bucket = template["resources"][1]
    bucket.update(name="bucket", id="bucket")
    payload["resources"].append(bucket)
    connection = template["connections"][0]
    connection.update(target="bucket", target_id="bucket")
    payload["connections"].append(connection)


def test_native_delivery_waits_for_trail_owned_role_policy():
    tree = generate(architecture())
    trail = resources(tree, "aws_cloudtrail")[0]
    assert (
        "trimsuffix(var.cloud_watch_logs_group_arn"
        in trail["cloud_watch_logs_group_arn"]
    )
    assert (
        trail["cloud_watch_logs_role_arn"]
        == "${aws_iam_role.source-resource_cloudwatch_logs.arn}"
    )
    assert trail["depends_on"] == [
        "${aws_iam_role_policy.source-resource_cloudwatch_logs}"
    ]
    assert len(trail["lifecycle"][0]["precondition"]) == 3
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    role = resources(tree, "aws_iam_role")[0]
    assert role["name_prefix"] == "cloudtrail-logs-"
    assert (
        "cloudtrail.${data.aws_partition.cloudtrail_logs.dns_suffix}"
        in role["assume_role_policy"]
    )
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert "logs:CreateLogStream" in policy["policy"]
    assert "logs:PutLogEvents" in policy["policy"]
    assert "log-stream:" in policy["policy"]
    assert "_CloudTrail_" in policy["policy"]
    assert "kms:" not in policy["policy"]
    assert "aws_cloudtrail." not in file_with(
        tree, "/source-resource/cloudwatch_logs.tf"
    )
    assert (
        "cloud_watch_logs_group_arn = module.target-resource.log_group_arn"
        in file_with(tree, "/environments/dev/main.tf")
    )
    contribution = ConnectionProcessor().process_all(project(architecture()))
    assert contribution.iam == []
    assert not any(path.endswith("/iam.tf") for path in tree)


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_shared_group_owns_no_delivery_roles_and_each_trail_aggregates_once(
    names, duplicate
):
    payload = architecture()
    first = deepcopy(payload["resources"][0])
    base_connection = deepcopy(payload["connections"][0])
    payload["resources"] = payload["resources"][1:]
    payload["connections"] = []
    for name in names:
        trail = deepcopy(first)
        trail.update(name=f"trail-{name}", id=f"trail-{name}")
        trail["config"]["trail_name"] = f"audit-{name}"
        payload["resources"].append(trail)
        connection = deepcopy(base_connection)
        connection.update(source=trail["name"], source_id=trail["id"])
        payload["connections"].append(connection)
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == len(names)
    assert len(resources(tree, "aws_iam_role_policy")) == len(names)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree
    assert not any("/target-resource/cloudwatch_logs.tf" in path for path in tree)


def test_two_log_groups_are_rejected_before_generation_and_preview():
    payload = architecture()
    other = deepcopy(payload["resources"][1])
    other.update(name="other", id="other")
    payload["resources"].append(other)
    payload["connections"].append(
        dict(payload["connections"][0], target="other", target_id="other")
    )
    for operation in (
        generate,
        lambda payload: ConnectionPreviewer().preview_all(project(payload)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match="only one CloudWatch"):
            operation(payload)


@pytest.mark.parametrize(
    "source,target",
    [("us-west-2", None), (None, "us-west-2"), ("us-east-1", "us-west-2")],
)
def test_effective_home_regions_must_match(source, target):
    payload = architecture()
    payload["resources"][0]["provider_region"] = source
    payload["resources"][1]["provider_region"] = target
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_environment_region_override_can_place_implicit_peer_together():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-west-2"
    payload["environments"][0]["variables"]["region"] = "eu-west-1"
    assert resources(generate(payload), "aws_cloudtrail")
    payload["environments"].append({"name": "other", "variables": {}})
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


@pytest.mark.parametrize("bucket", ["", "external-audit-bucket", "managed"])
def test_preview_reports_missing_s3_delivery_only_when_unconfigured(bucket):
    payload = architecture()
    payload["resources"][0]["config"]["s3_bucket_name"] = (
        "" if bucket == "managed" else bucket
    )
    if bucket == "managed":
        connect_bucket(payload)
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert any("S3 delivery bucket" in issue.message for issue in preview.issues) == (
        bucket == ""
    )
    assert {(item.module, item.resource_type) for item in preview.resources} == {
        ("source-resource", "aws_iam_role"),
        ("source-resource", "aws_iam_role_policy"),
    }


@pytest.mark.parametrize("external", [False, True])
def test_encrypted_log_groups_grant_only_selected_key_via_logs(external):
    payload = architecture()
    if external:
        payload["resources"][1]["config"]["kms_key_id"] = "alias/audit"
    else:
        connect_key(payload, "target-resource")
    tree = generate(payload)
    policy = file_with(tree, "/source-resource/cloudwatch_logs.tf")
    assert '"kms:ViaService"' in policy
    assert (
        '"logs.${data.aws_region.cloudtrail_logs.region}.${data.aws_partition.cloudtrail_logs.dns_suffix}"'
        in policy
    )
    for action in (
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey",
    ):
        assert action in policy
    assert ("data.aws_kms_key.kms_access_target-resource_arn.arn" in policy) == external
    main = file_with(tree, "/environments/dev/main.tf")
    assert ("kms_access_target-resource_arn = module.key.key_arn" in main) == (
        not external
    )
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert any("external KMS" in issue.message for issue in preview.issues) == external
    assert not any(path.endswith("/iam.tf") for path in tree)
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_unconnected_trails_keep_existing_native_configuration():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    trail = resources(tree, "aws_cloudtrail")[0]
    assert not any(key.startswith("cloud_watch_logs") for key in trail)
    assert "depends_on" not in trail
    assert "lifecycle" not in trail
    assert not resources(tree, "aws_iam_role")
    assert not any(path.endswith("/cloudwatch_logs.tf") for path in tree)


def test_empty_config_and_connection_direction_are_registered():
    spec = resolve_spec(ServiceType.CLOUDTRAIL, ServiceType.CLOUDWATCH, None, {})
    assert spec.connection_type == "logs_to"
    assert spec.config_model is EmptyConnectionConfig
    assert spec.region_policy == "same-region"
    assert (
        resolve_spec(ServiceType.CLOUDWATCH, ServiceType.CLOUDTRAIL, None, {}) is None
    )
    with pytest.raises(ValidationError):
        EmptyConnectionConfig(role_arn="external")


@needs_terraform
@pytest.mark.parametrize(
    "multi,partition,region,account,suffix",
    [
        (True, "aws", "us-east-1", "123456789012", ""),
        (False, "aws", "us-east-1", "123456789012", ":*"),
        (False, "aws-us-gov", "us-gov-west-1", "123456789012", ""),
    ],
)
def test_native_stream_scopes_and_wildcard_normalization(
    tmp_path, multi, partition, region, account, suffix
):
    arn = f"arn:{partition}:logs:{region}:{account}:log-group:/audit/trail"
    expression = str(cloudtrail_log_stream_arn())
    replacements = {
        "var.cloud_watch_logs_group_arn": json.dumps(arn + suffix),
        "var.is_multi_region_trail": str(multi).lower(),
        "data.aws_caller_identity.cloudtrail_logs.account_id": json.dumps(account),
        "data.aws_region.cloudtrail_logs.region": json.dumps(region),
    }
    for key, value in replacements.items():
        expression = expression.replace(key, value)
    result = subprocess.run(
        ["terraform", "console"],
        input=expression,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (
        json.loads(result.stdout)
        == f"{arn}:log-stream:{account}_CloudTrail_{'' if multi else region}*"
    )


@needs_terraform
@pytest.mark.parametrize(
    "arn,expected",
    [
        ("arn:aws:logs:us-east-1:123456789012:log-group:audit", [True, True, True]),
        ("arn:aws:logs:us-east-1:123456789012:log-group:audit:*", [True, True, True]),
        ("arn:aws:logs:us-west-2:123456789012:log-group:audit", [True, False, True]),
        ("arn:aws:logs:us-east-1:999999999999:log-group:audit", [True, True, False]),
        (
            "arn:aws-us-gov:logs:us-east-1:123456789012:log-group:audit",
            [True, False, True],
        ),
        ("invalid", [False, False, False]),
        ("arn:aws:s3:us-east-1:123456789012:log-group:audit", [False, True, True]),
    ],
)
def test_native_destination_guards_reject_scope_overrides(tmp_path, arn, expected):
    expressions = [str(item["condition"]) for item in cloudtrail_logs_preconditions()]
    replacements = {
        "var.cloud_watch_logs_group_arn": json.dumps(arn),
        "data.aws_partition.cloudtrail_logs.partition": '"aws"',
        "data.aws_region.cloudtrail_logs.region": '"us-east-1"',
        "data.aws_caller_identity.cloudtrail_logs.account_id": '"123456789012"',
    }
    for key, value in replacements.items():
        expressions = [expression.replace(key, value) for expression in expressions]
    result = subprocess.run(
        ["terraform", "console"],
        input="[" + ", ".join(expressions) + "]",
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert re.findall(r"\b(true|false)\b", result.stdout) == [
        str(value).lower() for value in expected
    ]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize("mode", ["plain", "shared", "managed_key", "external_key"])
def test_delivery_projects_validate_and_have_no_dependency_cycles(tmp_path, mode):
    payload = architecture()
    connect_bucket(payload)
    if mode == "shared":
        second = deepcopy(payload["resources"][0])
        second.update(name="second", id="second")
        second["config"]["trail_name"] = "second-audit"
        payload["resources"].append(second)
        payload["connections"].extend(
            [
                dict(item, source="second", source_id="second")
                for item in list(payload["connections"])
            ]
        )
    elif mode == "managed_key":
        connect_key(payload, "source-resource")
        connect_key(payload, "target-resource")
    elif mode == "external_key":
        payload["resources"][1]["config"]["kms_key_id"] = "alias/audit"
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    env = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env.parent)
    _run_terraform(["validate"], env.parent)
    _run_terraform(["graph", "-type=plan"], env.parent)
