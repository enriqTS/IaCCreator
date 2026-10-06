"""Config notification policies, supported destinations, and dependency ordering."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.aws_config_notifications import (
    config_sns_preconditions,
    config_topic_preconditions,
)
from app.models.connection_configs.configs import EmptyConnectionConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cloudtrail_logs_connections import connect_bucket, connect_key
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
        resolve_spec(ServiceType.AWS_CONFIG, ServiceType.SNS, None, {})
    )
    payload["resources"][0]["config"].update(
        role_arn="arn:aws:iam::123456789012:role/config-recorder",
        s3_bucket_name="external-config-bucket",
    )
    return payload


def mixed_architecture():
    payload = architecture()
    connect_bucket(payload)
    payload["connections"].append(
        {
            "source": "bucket",
            "source_id": "bucket",
            "target": "target-resource",
            "target_id": "tgt",
            "connection_type": "notifies",
        }
    )
    return payload


def test_native_delivery_and_topic_owned_policy_keep_recorder_ordering():
    payload = architecture()
    tree = generate(payload)
    channel = resources(tree, "aws_config_delivery_channel")[0]
    assert channel["sns_topic_arn"] == "${var.sns_topic_arn}"
    assert channel["s3_bucket_name"] == "${var.s3_bucket_name}"
    assert channel["depends_on"] == [
        "${aws_config_configuration_recorder.source-resource}"
    ]
    assert len(channel["lifecycle"][0]["precondition"]) == 2
    status = resources(tree, "aws_config_configuration_recorder_status")[0]
    assert status["depends_on"] == ["${aws_config_delivery_channel.source-resource}"]
    policy = resources(tree, "aws_sns_topic_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 2
    content = file_with(tree, "/target-resource/policy_s3_delivery.tf")
    assert '"config.${data.aws_partition.topic_delivery.dns_suffix}"' in content
    assert '"AWS:SourceAccount"' in content and '"AWS:SourceArn"' in content
    assert "var.config_source-resource_source_arn" in content
    assert "SNS:SetTopicAttributes" in content and '"AWS:SourceOwner"' in content
    assert "aws_config_configuration_recorder." not in content
    assert "module." not in content
    source_outputs = file_with(tree, "/source-resource/outputs.tf")
    identity = source_outputs.split('output "notification_source_arn"')[1].split(
        "\n}\n"
    )[0]
    assert ":config:" in identity and ":*" in identity
    assert "aws_config_" not in identity and "depends_on" not in identity
    assert (
        "sns_topic_arn = module.target-resource.config_notification_arn"
        in file_with(tree, "/environments/dev/main.tf")
    )
    target_outputs = file_with(tree, "/target-resource/outputs.tf")
    assert "depends_on = [aws_sns_topic_policy.s3_delivery]" in target_outputs
    assert not resources(tree, "aws_iam_role")
    assert not resources(tree, "aws_iam_role_policy")
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert {(item.module, item.resource_type) for item in preview.resources} == {
        ("target-resource", "aws_sns_topic_policy")
    }
    assert not preview.iam and not preview.issues


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=20)
def test_shared_topic_policies_are_deterministic_for_source_names(names, duplicate):
    payload = mixed_architecture()
    template = deepcopy(payload["resources"][0])
    connections = [
        item for item in payload["connections"] if item["source"] == "source-resource"
    ]
    payload["resources"] = payload["resources"][1:]
    payload["connections"] = [
        item for item in payload["connections"] if item["source"] != "source-resource"
    ]
    for name in names:
        source = deepcopy(template)
        source.update(name=f"recorder-{name}", id=f"recorder-{name}")
        source["config"]["recorder_name"] = f"recorder-{name}"
        payload["resources"].append(source)
        payload["connections"].extend(
            dict(item, source=source["name"], source_id=source["id"])
            for item in connections
        )
    tree = generate(payload)
    policy = file_with(tree, "/target-resource/policy_s3_delivery.tf")
    assert len(resources(tree, "aws_sns_topic_policy")) == 1
    assert policy.count('"ConfigDelivery') == len(names)
    assert policy.count('"S3Delivery"') == 1
    assert policy.count('"OwnerAccess"') == 1
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "field,value",
    [
        ("fifo_topic", True),
        ("topic_name", "unsupported.fifo"),
        ("kms_master_key_id", "alias/aws/sns"),
        ("kms_master_key_id", "alias/customer"),
        ("kms_master_key_id", "arn:aws:kms:us-east-1:123456789012:key/example"),
    ],
)
def test_unsupported_topic_configurations_fail_generation_and_preview(field, value):
    payload = architecture()
    payload["resources"][1]["config"][field] = value
    for operation in (
        generate,
        lambda data: ConnectionPreviewer().preview_all(project(data)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match="standard|encrypted"):
            operation(payload)


def test_managed_encryption_rejected_independent_of_connector_order():
    payload = architecture()
    connect_key(payload, "target-resource")
    for _ in range(2):
        with pytest.raises(InvalidConnectionConfigError, match="encrypted"):
            generate(payload)
        with pytest.raises(InvalidConnectionConfigError, match="encrypted"):
            ConnectionPreviewer().preview_all(project(payload))
        payload["connections"].reverse()


def test_multiple_topics_fail_generation_and_preview():
    payload = architecture()
    topic = deepcopy(payload["resources"][1])
    topic.update(name="other", id="other")
    topic["config"]["topic_name"] = "other"
    payload["resources"].append(topic)
    payload["connections"].append(
        dict(payload["connections"][0], target="other", target_id="other")
    )
    for operation in (
        generate,
        lambda data: ConnectionPreviewer().preview_all(project(data)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match="only one SNS"):
            operation(payload)


@pytest.mark.parametrize(
    "source,target",
    [("us-west-2", None), (None, "us-west-2"), ("us-east-1", "us-west-2")],
)
def test_effective_regions_must_match(source, target):
    payload = architecture()
    payload["resources"][0]["provider_region"] = source
    payload["resources"][1]["provider_region"] = target
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_every_environment_checks_effective_regions():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-west-2"
    payload["environments"][0]["variables"]["region"] = "eu-west-1"
    assert resources(generate(payload), "aws_config_delivery_channel")
    payload["environments"].append({"name": "other", "variables": {}})
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


@pytest.mark.parametrize(
    "role,bucket", [(False, ""), (True, ""), (True, "external"), (True, "managed")]
)
def test_preview_reports_remaining_recorder_and_bucket_prerequisites(role, bucket):
    payload = architecture()
    payload["resources"][0]["config"].update(
        role_arn="arn:aws:iam::123456789012:role/recorder" if role else "",
        s3_bucket_name="" if bucket == "managed" else bucket,
    )
    if bucket == "managed":
        connect_bucket(payload)
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert any("recorder IAM role" in issue.message for issue in preview.issues) == (
        not role
    )
    assert any("S3 delivery bucket" in issue.message for issue in preview.issues) == (
        bucket == ""
    )


def test_unconnected_recorder_and_topic_keep_existing_configuration():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    channel = resources(tree, "aws_config_delivery_channel")[0]
    assert "sns_topic_arn" not in channel and "lifecycle" not in channel
    assert not resources(tree, "aws_sns_topic_policy")
    assert "notification_source" not in file_with(tree, "/source-resource/outputs.tf")
    assert "topic_delivery" not in "\n".join(tree.values())


def test_native_registry_uses_typed_empty_config_and_same_region():
    spec = resolve_spec(ServiceType.AWS_CONFIG, ServiceType.SNS, None, {})
    assert spec.connection_type == "notifies"
    assert spec.config_model is EmptyConnectionConfig
    assert spec.region_policy == "same-region"
    assert resolve_spec(ServiceType.SNS, ServiceType.AWS_CONFIG, None, {}) is None


@needs_terraform
@pytest.mark.parametrize(
    "arn,expected",
    [
        ("arn:aws:sns:us-east-1:123456789012:config", [True, True]),
        ("arn:aws:sns:us-east-1:999999999999:config", [True, True]),
        ("arn:aws:sns:us-west-2:123456789012:config", [True, False]),
        ("arn:aws-us-gov:sns:us-east-1:123456789012:config", [True, False]),
        ("arn:aws:sns:us-east-1:123456789012:config.fifo", [False, True]),
        ("arn:aws:sqs:us-east-1:123456789012:config", [False, True]),
        ("invalid", [False, False]),
    ],
)
def test_native_channel_guards_allow_cross_account_and_reject_scope_overrides(
    tmp_path, arn, expected
):
    expressions = [str(item["condition"]) for item in config_sns_preconditions()]
    replacements = {
        "var.sns_topic_arn": json.dumps(arn),
        "data.aws_partition.config_notifications.partition": '"aws"',
        "data.aws_region.config_notifications.region": '"us-east-1"',
    }
    check_console(tmp_path, expressions, replacements, expected)


def check_console(directory, expressions, replacements, expected):
    for key, value in replacements.items():
        expressions = [expression.replace(key, value) for expression in expressions]
    result = subprocess.run(
        ["terraform", "console"],
        input="[" + ", ".join(expressions) + "]",
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert re.findall(r"\b(true|false)\b", result.stdout) == [
        str(value).lower() for value in expected
    ]


@needs_terraform
@pytest.mark.parametrize(
    "fifo,key,expected",
    [
        (False, "", [True, True]),
        (False, None, [True, True]),
        (False, "alias/key", [True, False]),
        (True, "", [False, True]),
    ],
)
def test_native_topic_guards_check_actual_topic_attributes(
    tmp_path, fifo, key, expected
):
    expressions = [
        str(item["condition"]) for item in config_topic_preconditions("topic")
    ]
    check_console(
        tmp_path,
        expressions,
        {
            "aws_sns_topic.topic.fifo_topic": json.dumps(fifo),
            "aws_sns_topic.topic.kms_master_key_id": json.dumps(key),
        },
        expected,
    )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize("mixed", [False, True])
def test_projects_validate_without_delivery_dependency_cycles(tmp_path, mixed):
    payload = mixed_architecture() if mixed else architecture()
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
