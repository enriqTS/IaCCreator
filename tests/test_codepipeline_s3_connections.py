"""Artifact connections require real stages and preserve action configuration."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.models.input_models.codepipeline_config import CodePipelineConfig
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
        resolve_spec(ServiceType.CODEPIPELINE, ServiceType.S3, "stores_artifacts", {})
    )


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_artifact_store_preserves_configured_stages():
    text = "\n".join(generate(architecture()).values())
    assert "artifact_store {" in text
    assert 'dynamic "stage"' in text
    assert 'dynamic "action"' in text
    assert "module.target-resource.bucket_name" in text
    assert '"s3:PutObject"' in text
    assert "depends_on = [aws_iam_role_policy.artifacts]" in text
    assert "external-source" in text
    assert "managed-by-connection" not in text


def test_duplicate_artifact_connection_is_idempotent():
    payload = architecture()
    expected = generate(payload)
    payload["connections"] *= 2
    assert generate(payload) == expected


@pytest.mark.parametrize(
    "stages", ["invalid", "{}", '[{"name":"Source","actions":[]}]']
)
def test_invalid_stage_json_is_rejected(stages):
    with pytest.raises(ValidationError):
        CodePipelineConfig(stages_json=stages)


def test_artifact_connection_requires_stages():
    payload = architecture()
    payload["resources"][0]["config"]["stages_json"] = "[]"
    with pytest.raises(InvalidConnectionConfigError, match="configured stages"):
        generate(payload)


def test_cross_region_actions_are_rejected():
    payload = architecture()
    config = payload["resources"][0]["config"]
    stages = json.loads(config["stages_json"])
    stages[1]["actions"][0]["region"] = "eu-west-1"
    config["stages_json"] = json.dumps(stages)
    with pytest.raises(InvalidConnectionConfigError, match="cross-region artifact"):
        generate(payload)


@needs_terraform
def test_encrypted_artifacts_validate_without_cycles(tmp_path):
    payload = architecture()
    payload["resources"].append(
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Artifact encryption"},
        }
    )
    payload["connections"].append(
        {"source": "key", "target": "target-resource", "connection_type": "encrypts"}
    )
    tree = generate(payload)
    assert '"kms:GenerateDataKey*"' in "\n".join(tree.values())
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
