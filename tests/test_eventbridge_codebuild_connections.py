"""EventBridge CodeBuild targets use one project and a scoped rule role."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models.connection_configs.eventbridge_codebuild import (
    EventBridgeCodeBuildConfig,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.CODEBUILD, None, {})
    )


def test_target_starts_only_the_connected_project():
    tree = generate(architecture())
    target = next(v for k, v in tree.items() if "/build_" in k)
    assert '"codebuild:StartBuild"' in target
    assert "codebuild:StartBuildBatch" not in target
    assert "events.amazonaws.com" in target
    assert "aws_cloudwatch_event_rule.source-resource.arn" in target
    assert "role_arn = aws_iam_role.build_" in target
    assert "module.target-resource.project_arn" in "\n".join(tree.values())
    assert "input =" not in target
    assert generate(architecture()) == tree


def test_distinct_target_ids_create_distinct_build_targets():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"target_id": "first"}
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {"target_id": "second"}
    payload["connections"].append(other)
    tree = generate(payload)
    assert (
        sum('resource "aws_cloudwatch_event_target"' in v for v in tree.values()) == 2
    )
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_invalid_target_id_rejected():
    with pytest.raises(ValidationError):
        EventBridgeCodeBuildConfig(target_id="invalid/target")


def test_unvalidated_build_overrides_rejected():
    with pytest.raises(ValidationError):
        EventBridgeCodeBuildConfig(input='{"buildType":"BATCH"}')


@needs_terraform
def test_codebuild_target_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
