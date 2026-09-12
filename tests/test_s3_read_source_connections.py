"""Source connections grant scoped reads and preserve prerequisite ordering."""

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


@pytest.fixture(params=[ServiceType.MWAA, ServiceType.COMPREHEND])
def payload(request):
    return connection_architecture(resolve_spec(request.param, ServiceType.S3, "", {}))


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_source_policy_and_native_reference(payload):
    if payload["resources"][0]["service_type"] == ServiceType.COMPREHEND.value:
        payload["connections"][0]["connection_config"] = {"prefix": "training/data.csv"}
    text = "\n".join(generate(payload).values())
    assert 'resource "aws_iam_role_policy" "source_data"' in text
    assert '"s3:GetObjectVersion"' in text
    assert '"s3:PutObject"' not in text
    assert "aws_iam_role_policy.source_data]" in text
    assert "managed-by-connection" not in text
    if payload["resources"][0]["service_type"] == ServiceType.MWAA.value:
        assert "module.target-resource.workflow_bucket_arn" in text
        assert (
            "depends_on = [aws_s3_bucket_versioning.target-resource_versioning]" in text
        )
    else:
        assert '"training/data.csv"' in text
        assert '"training/data.csv*"' in text


def test_duplicate_source_is_idempotent(payload):
    expected = generate(payload)
    payload["connections"] *= 2
    assert generate(payload) == expected


def test_source_requires_external_role(payload):
    config = payload["resources"][0]["config"]
    config[
        "execution_role_arn"
        if "execution_role_arn" in config
        else "data_access_role_arn"
    ] = ""
    with pytest.raises(InvalidConnectionConfigError, match="external service role"):
        generate(payload)


@needs_terraform
def test_source_with_managed_key_has_no_cycles(payload, tmp_path):
    payload["resources"].append(
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Source encryption"},
        }
    )
    payload["connections"].append(
        {"source": "key", "target": "target-resource", "connection_type": "encrypts"}
    )
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "module.key.key_arn" in text
    assert '"kms:Decrypt"' in text
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
