"""Audit delivery shares bucket permissions without resource dependency cycles."""

from copy import deepcopy

import pytest

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture():
    payload = connection_architecture(
        resolve_spec(ServiceType.CLOUDTRAIL, ServiceType.S3, "delivers_to", {})
    )
    payload["resources"].append(
        {
            "name": "recorder",
            "service_type": ServiceType.AWS_CONFIG.value,
            "config": {
                "recorder_name": "audit",
                "role_arn": "arn:aws:iam::123456789012:role/config",
            },
        }
    )
    payload["connections"].append(
        {
            "source": "recorder",
            "target": "target-resource",
            "connection_type": "delivers_to",
        }
    )
    return payload


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_delivery_permissions_are_scoped_and_aggregated():
    tree = generate(architecture())
    policy = next(
        text for path, text in tree.items() if path.endswith("bucket_policy.tf")
    )
    assert policy.count('resource "aws_s3_bucket_policy"') == 1
    assert '"cloudtrail.amazonaws.com"' in policy
    assert '"config.amazonaws.com"' in policy
    assert '"aws:SourceArn"' in policy
    assert '"aws:SourceAccount"' in policy
    assert '"s3:ListBucket"' in policy
    assert "/Config/*" in policy
    assert "bucket-owner-full-control" in policy
    main = tree["connection-check/environments/dev/main.tf"]
    assert main.count("module.target-resource.delivery_bucket_name") == 2
    assert "module.source-resource.encryption_trail_arn" in main
    assert "managed-by-connection" not in "\n".join(tree.values())


def test_duplicates_and_connection_order_do_not_change_delivery():
    payload = architecture()
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


def test_multiple_delivery_buckets_are_rejected():
    payload = architecture()
    payload["resources"].append(
        {"name": "other", "service_type": "s3", "config": {"bucket_prefix": "other-"}}
    )
    payload["connections"].append(
        {"source": "recorder", "target": "other", "connection_type": "delivers_to"}
    )
    with pytest.raises(
        InvalidConnectionConfigError, match="one managed delivery bucket"
    ):
        generate(payload)


@needs_terraform
def test_mixed_delivery_validates_without_cycles(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
