"""Private origins compose safely with audit delivery and managed encryption."""

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
    return connection_architecture(
        resolve_spec(ServiceType.CLOUDFRONT, ServiceType.S3, "origin", {})
    )


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_signed_private_origin_and_read_only_permissions():
    text = "\n".join(generate(architecture()).values())
    assert 'resource "aws_cloudfront_origin_access_control"' in text
    assert 'signing_behavior = "always"' in text
    assert "custom_origin_config" not in text
    assert "s3_origin_config {" in text
    assert '"s3:GetObject"' in text
    assert '"s3:PutObject"' not in text
    assert '"DELETE"' not in text
    assert "module.target-resource.bucket_regional_domain_name" in text
    assert "module.source-resource.distribution_arn" in text


def mixed_architecture():
    payload = architecture()
    payload["resources"] += [
        {
            "name": "other",
            "service_type": "cloudfront",
            "config": {"origin_id": "other"},
        },
        {
            "name": "trail",
            "service_type": "cloudtrail",
            "config": {"trail_name": "audit"},
        },
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Origin encryption"},
        },
    ]
    payload["connections"] += [
        {"source": "other", "target": "target-resource", "connection_type": "origin"},
        {
            "source": "trail",
            "target": "target-resource",
            "connection_type": "delivers_to",
        },
        {"source": "key", "target": "target-resource", "connection_type": "encrypts"},
        {"source": "key", "target": "trail", "connection_type": "encrypts"},
    ]
    return payload


def test_shared_policy_is_deterministic():
    payload = mixed_architecture()
    expected = generate(payload)
    text = "\n".join(expected.values())
    assert text.count('resource "aws_s3_bucket_policy"') == 1
    assert text.count('resource "aws_kms_key_policy"') == 1
    assert "s3_distribution_arns" in text
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


def test_multiple_origins_are_rejected():
    payload = architecture()
    payload["resources"].append(
        {"name": "other", "service_type": "s3", "config": {"bucket_prefix": "other-"}}
    )
    payload["connections"].append(
        {"source": "source-resource", "target": "other", "connection_type": "origin"}
    )
    with pytest.raises(InvalidConnectionConfigError, match="one managed S3 origin"):
        generate(payload)


@needs_terraform
def test_shared_encrypted_origin_has_no_cycles(tmp_path):
    _write_tree(tmp_path, generate(mixed_architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
