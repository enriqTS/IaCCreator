"""Firehose delivery owns native destination settings and scoped permissions."""

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
        resolve_spec(ServiceType.KINESIS_FIREHOSE, ServiceType.S3, "delivers_to", {})
    )
    payload["connections"][0]["connection_config"] = {"prefix": "events/"}
    return payload


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_native_s3_configuration_and_scoped_policy():
    tree = generate(architecture())
    text = "\n".join(tree.values())
    assert "extended_s3_configuration {" in text
    assert "module.target-resource.bucket_arn" in text
    assert '"s3:PutObject"' in text
    assert 'format("%s/%s*", var.bucket_arn, var.s3_prefix)' in text
    assert "depends_on = [aws_iam_role_policy.s3_delivery]" in text
    assert "managed-by-connection" not in text


def test_duplicates_are_idempotent():
    payload = architecture()
    expected = generate(payload)
    payload["connections"] *= 2
    assert generate(payload) == expected


@pytest.mark.parametrize("override", [{"role_arn": None}, {"destination": "redshift"}])
def test_incompatible_destination_or_missing_role_is_rejected(override):
    payload = architecture()
    payload["resources"][0]["config"].update(override)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@needs_terraform
def test_encrypted_delivery_validates_without_cycles(tmp_path):
    payload = architecture()
    payload["resources"].append(
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Delivery encryption"},
        }
    )
    payload["connections"].append(
        {"source": "key", "target": "target-resource", "connection_type": "encrypts"}
    )
    tree = generate(payload)
    assert '"kms:GenerateDataKey"' in "\n".join(tree.values())
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
