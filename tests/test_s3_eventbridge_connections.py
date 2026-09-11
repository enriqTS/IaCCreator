"""S3 EventBridge delivery aggregates independently of direct notifications."""

import json
from copy import deepcopy

import pytest

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.S3, ServiceType.EVENTBRIDGE, "delivers_to", {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def test_rule_scopes_managed_buckets_and_preserves_other_filters():
    payload = architecture()
    payload["resources"][1]["config"]["event_pattern"] = json.dumps(
        {
            "source": ["external"],
            "detail-type": ["Object Created"],
            "detail": {
                "object": {"key": [{"prefix": "incoming/"}]},
                "bucket": {"name": ["old"]},
            },
        }
    )
    tree = CodeGenerator().generate(project(payload))
    main = tree["connection-check/environments/dev/main.tf"]
    assert "module.source-resource.bucket_name" in main
    assert "source = [\n" in main and '"aws.s3"' in main
    assert '"Object Created"' in main and '"incoming/"' in main
    assert '"old"' not in main and '"external"' not in main
    notification = tree[
        "connection-check/modules/storage/s3/source-resource/notifications.tf"
    ]
    assert "eventbridge = true" in notification
    previews = ConnectionPreviewer().preview_all(project(payload))
    assert previews[0].resources[0].module == "source-resource"
    assert not previews[0].iam


@pytest.mark.parametrize(
    "override",
    [
        {"bus_name": "custom"},
        {"bus_name": "default"},
        {"schedule_expression": "rate(5 minutes)"},
        {"event_pattern": "[]"},
        {"event_pattern": "broken"},
        {"event_pattern": '{"detail": []}'},
        {"event_pattern": '{"$or": []}'},
    ],
)
def test_unsupported_rule_config_is_rejected(override):
    payload = architecture()
    payload["resources"][1]["config"].update(override)
    with pytest.raises(InvalidConnectionConfigError):
        CodeGenerator().generate(project(payload))


def mixed_architecture():
    payload = architecture()
    payload["resources"] += [
        {
            "name": "second",
            "service_type": "s3",
            "config": {
                "bucket_prefix": "second-",
                "notification_sns_arn": "arn:aws:sns:us-east-1:123456789012:external",
            },
        },
        {"name": "queue", "service_type": "sqs", "config": {"queue_name": "queue"}},
    ]
    payload["connections"] += [
        {
            "source": "second",
            "target": "target-resource",
            "connection_type": "delivers_to",
        },
        {"source": "source-resource", "target": "queue", "connection_type": "notifies"},
        {"source": "target-resource", "target": "queue", "connection_type": "targets"},
    ]
    return payload


def test_converging_buckets_and_direct_notifications_are_deterministic():
    payload = mixed_architecture()
    expected = CodeGenerator().generate(project(payload))
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert CodeGenerator().generate(project(payload)) == expected
    text = "\n".join(expected.values())
    assert text.count('resource "aws_s3_bucket_notification"') == 2
    assert text.count("eventbridge = true") == 2
    assert "var.notification_sns_arn" in text
    assert (
        "module.second.bucket_name"
        in expected["connection-check/environments/dev/main.tf"]
    )


@needs_terraform
def test_generated_delivery_project_validates_and_has_no_cycles(tmp_path):
    _write_tree(tmp_path, CodeGenerator().generate(project(mixed_architecture())))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
