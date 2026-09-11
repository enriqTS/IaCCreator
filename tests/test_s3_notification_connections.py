"""Bucket notifications aggregate without losing external destinations."""

from copy import deepcopy
from itertools import permutations

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.storage import S3NotificationConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.reference_project import reference_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def test_multiple_lambda_notifications_are_deterministic_and_preserve_external():
    architecture = reference_architecture()
    bucket = next(item for item in architecture.resources if item.name == "uploads")
    bucket.config.notification_sqs_arn = "arn:aws:sqs:us-east-1:123456789012:external"
    original = next(
        item for item in architecture.connections if item.source == "uploads"
    )
    second = original.model_copy(
        update={
            "target": "on-change",
            "target_id": None,
            "connection_config": {"filter_suffix": ".json"},
        }
    )
    others = [item for item in architecture.connections if item is not original]
    results = []
    for connections in permutations([original, second, original]):
        candidate = ArchitectureDescription.model_validate(architecture.model_dump())
        candidate.connections = [*others, *connections]
        tree = CodeGenerator().generate(IRBuilder().build(candidate))
        content = tree["reference-project/modules/storage/s3/uploads/notifications.tf"]
        assert content.count("lambda_function {") == 2
        assert "var.notification_sqs_arn" in content
        assert "aws_lambda_permission.on_change_permission" in content
        assert (
            sum(
                text.count('resource "aws_s3_bucket_notification"')
                for text in tree.values()
            )
            == 1
        )
        results.append(tree)
    assert all(tree == results[0] for tree in results)


def delivery_architecture(service):
    return connection_architecture(
        resolve_spec(ServiceType.S3, service, "notifies", {})
    )


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


@pytest.mark.parametrize("service", [ServiceType.SNS, ServiceType.SQS])
def test_delivery_ownership_and_policy_ready_reference(service):
    payload = delivery_architecture(service)
    ir = IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert any(
        item.resource_type
        == f"aws_{service.value}_{'topic' if service == ServiceType.SNS else 'queue'}_policy"
        and item.module == "target-resource"
        for item in preview.resources
    )
    assert any(
        item.resource_type == "aws_s3_bucket_notification"
        and item.module == "source-resource"
        for item in preview.resources
    )
    tree = CodeGenerator().generate(ir)
    contents = "\n".join(tree.values())
    assert (
        "target_resource_notification_arn = module.target-resource.s3_notification_arn"
        in contents
    )
    assert "s3.amazonaws.com" in contents
    assert "module.source-resource.bucket_arn" in contents
    outputs = next(
        text
        for path, text in tree.items()
        if path.endswith("/target-resource/outputs.tf")
    )
    assert "depends_on = [aws_" in outputs
    assert "notification_arn" in outputs
    assert not preview.iam


@pytest.mark.parametrize(
    "service, field", [(ServiceType.SNS, "fifo_topic"), (ServiceType.SQS, "fifo_queue")]
)
def test_fifo_destinations_rejected(service, field):
    payload = delivery_architecture(service)
    payload["resources"][1]["config"][field] = True
    with pytest.raises(InvalidConnectionConfigError, match="standard"):
        generate(payload)


@pytest.mark.parametrize(
    "events", [[], ["s3:MadeUp:*"], ["s3:ObjectCreated:*", "invalid"]]
)
def test_notification_event_validation(events):
    with pytest.raises(ValidationError):
        S3NotificationConfig(events=events)


@pytest.mark.parametrize("service", [ServiceType.SNS, ServiceType.SQS])
def test_external_keys_require_customer_policy(service):
    payload = delivery_architecture(service)
    payload["resources"][1]["config"]["kms_master_key_id"] = (
        f"alias/aws/{service.value}"
    )
    with pytest.raises(InvalidConnectionConfigError, match="customer-managed"):
        generate(payload)
    payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external"
    ir = IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert any("external KMS key owner" in item.message for item in preview.issues)


def mixed_delivery_architecture():
    payload = delivery_architecture(ServiceType.SQS)
    payload["resources"] += [
        {"name": "topic", "service_type": "sns", "config": {"topic_name": "topic"}},
        {
            "name": "second-bucket",
            "service_type": "s3",
            "config": {"bucket_name": "second-bucket"},
        },
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Notification key"},
        },
        {
            "name": "events",
            "service_type": "eventbridge",
            "config": {"rule_name": "events", "event_pattern": '{"source":["aws.s3"]}'},
        },
    ]
    payload["connections"][0]["connection_config"] = {"filter_suffix": ".json"}
    payload["connections"] += [
        {
            "source": "source-resource",
            "target": "topic",
            "connection_type": "notifies",
            "connection_config": {"filter_suffix": ".csv"},
        },
        {
            "source": "second-bucket",
            "target": "target-resource",
            "connection_type": "notifies",
        },
        {
            "source": "second-bucket",
            "target": "topic",
            "connection_type": "notifies",
            "connection_config": {"events": ["s3:ObjectRemoved:*"]},
        },
        {
            "source": "topic",
            "target": "target-resource",
            "connection_type": "delivers_to",
        },
        {"source": "events", "target": "target-resource", "connection_type": "targets"},
        *[
            {"source": "key", "target": target, "connection_type": "encrypts"}
            for target in ["source-resource", "topic", "target-resource"]
        ],
    ]
    return payload


def test_converging_publishers_share_policies_and_are_order_independent():
    payload = mixed_delivery_architecture()
    baseline = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == baseline
    contents = "\n".join(baseline.values())
    assert contents.count('resource "aws_sqs_queue_policy"') == 1
    assert contents.count('resource "aws_sns_topic_policy"') == 1
    assert contents.count('resource "aws_kms_key_policy"') == 1
    for publisher in ["s3", "sns", "eventbridge"]:
        assert f"var.delivery_{publisher}_arns" in contents
    key_policy = next(
        text for path, text in baseline.items() if path.endswith("/key/key_policy.tf")
    )
    assert key_policy.count('"s3.${data.aws_partition.kms_policy.dns_suffix}"') == 1
    assert "kms:Decrypt" in key_policy and "kms:GenerateDataKey" in key_policy


@needs_terraform
def test_mixed_notification_project_validates_without_cycles(tmp_path):
    _write_tree(tmp_path, generate(mixed_delivery_architecture()))
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)


@pytest.mark.parametrize(
    "filters", [{}, {"filter_prefix": "uploads/"}, {"filter_prefix": "uploads%2F"}]
)
def test_overlapping_managed_filters_are_rejected(filters):
    payload = mixed_delivery_architecture()
    payload["connections"][0]["connection_config"] = filters
    payload["connections"][1]["connection_config"] = {
        "filter_prefix": "uploads/",
        "filter_suffix": ".csv",
    }
    with pytest.raises(InvalidConnectionConfigError, match="must not overlap"):
        generate(payload)


@pytest.mark.parametrize("service", [ServiceType.SNS, ServiceType.SQS])
def test_notification_direction_and_legacy_resolution(service):
    assert resolve_spec(service, ServiceType.S3, "notifies", {}) is None
    spec = resolve_spec(ServiceType.S3, service, "", {})
    assert spec.connection_type == "notifies"
    assert spec.region_policy == "same-region"
    with pytest.raises(ValidationError):
        spec.config_model(unknown_option=True)
