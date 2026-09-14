"""Kinesis clients receive scoped data access without implicit stream consumers."""

import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

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


def architecture(source=ServiceType.LAMBDA, kind="reads_from"):
    return connection_architecture(resolve_spec(source, ServiceType.KINESIS, kind, {}))


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    kind=st.sampled_from(["reads_from", "writes_to"]),
)
def test_access_is_scoped_to_stream_and_runtime_role(source, kind):
    payload = architecture(source, kind)
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    statements = [
        statement
        for statement in policy["Statement"]
        if any(action.startswith("kinesis:") for action in statement["Action"])
    ]
    assert len(statements) == 1
    assert statements[0]["Resource"] == "${var.kinesis_target-resource_arn}"
    assert set(statements[0]["Action"]) == (
        {
            "kinesis:DescribeStream",
            "kinesis:DescribeStreamSummary",
            "kinesis:GetRecords",
            "kinesis:GetShardIterator",
            "kinesis:ListShards",
        }
        if kind == "reads_from"
        else {"kinesis:PutRecord", "kinesis:PutRecords"}
    )
    text = "\n".join(tree.values())
    assert "module.target-resource.stream_arn" in text
    assert "module.target-resource.stream_name" in text
    assert 'output "kinesis_target-resource_name"' in text
    assert "aws_lambda_event_source_mapping" not in text
    assert "aws_kinesis_stream_consumer" not in text
    assert "secretsmanager:GetSecretValue" not in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    assert ConnectionPreviewer().preview_all(project(payload))[0].issues


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_converging_stream_access_is_order_independent(source):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    payload["connections"].append(write)
    other = deepcopy(payload["resources"][1])
    other.update(id="other", name="other-stream")
    other["config"]["stream_name"] = "other-stream"
    payload["resources"].append(other)
    second = deepcopy(write)
    second.update(target="other-stream", target_id="other")
    payload["connections"].append(second)
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    policy = json.loads(
        expected["connection-check/iam-policies/source-resource-policy.json"]
    )
    assert (
        len([s for s in policy["Statement"] if s["Action"][0].startswith("kinesis:")])
        == 3
    )


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_default_connection_is_read_only(source):
    assert (
        resolve_spec(source, ServiceType.KINESIS, None, {}).connection_type
        == "reads_from"
    )


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_bidirectional_access_validates_without_dependency_cycles(source, tmp_path):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    payload["connections"].append(write)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
