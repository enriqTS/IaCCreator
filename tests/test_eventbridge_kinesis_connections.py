"""EventBridge stream targets keep partitioning and write permissions explicit."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.eventbridge_kinesis import EventBridgeKinesisConfig
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
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.KINESIS, None, {})
    )


@given(
    path=st.one_of(
        st.none(),
        st.lists(
            st.from_regex(r"[A-Za-z_][A-Za-z0-9_-]{0,12}", fullmatch=True),
            min_size=1,
            max_size=5,
        ).map(lambda fields: "$." + ".".join(fields)),
    ),
    constant=st.sampled_from([None, '{"job":"daily"}']),
)
def test_stream_role_and_partitioning_are_native_and_idempotent(path, constant):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "partition_key_path": path,
        "input": constant,
    }
    tree = generate(payload)
    target = next(v for k, v in tree.items() if "/stream_" in k)
    assert '"kinesis:PutRecord"' in target
    assert "kinesis:PutRecords" not in target
    assert "kinesis:GetRecords" not in target
    assert "events.amazonaws.com" in target
    assert "aws_cloudwatch_event_rule.source-resource.arn" in target
    assert "role_arn = aws_iam_role.stream_" in target
    assert ("kinesis_target" in target) == (path is not None)
    if path is not None:
        assert f'partition_key_path = "{path}"' in target
    assert ("input =" in target) == (constant is not None)
    assert "module.target-resource.stream_arn" in "\n".join(tree.values())
    stream = "\n".join(v for k, v in tree.items() if "/target-resource/" in k)
    assert "aws_cloudwatch_event_target" not in stream
    assert "module.source-resource" not in stream
    payload["connections"] *= 2
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "path",
    [
        "$",
        "detail.id",
        "$..id",
        "$.detail.*",
        "$.detail[0]",
        "$.detail.id\n",
        "$." + "a" * 255,
    ],
)
def test_unsupported_partition_paths_rejected(path):
    with pytest.raises(ValidationError):
        EventBridgeKinesisConfig(partition_key_path=path)


def test_partition_path_boundary_and_blank_default():
    assert EventBridgeKinesisConfig(partition_key_path="").partition_key_path is None
    assert (
        len(
            EventBridgeKinesisConfig(
                partition_key_path="$." + "a" * 254
            ).partition_key_path
        )
        == 256
    )
    fields = EventBridgeKinesisConfig.get_field_schema()
    assert any(field.key == "partition_key_path" for field in fields)


def test_same_target_id_rejects_different_partitioning():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "target_id": "job",
        "partition_key_path": "$.detail.first",
    }
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["partition_key_path"] = "$.detail.second"
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError, match="uniquely"):
        generate(payload)


def test_distinct_target_ids_preserve_multiple_partition_settings():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "target_id": "first",
        "partition_key_path": "$.detail.first",
    }
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {
        "target_id": "second",
        "partition_key_path": "$.detail.second",
    }
    payload["connections"].append(other)
    tree = generate(payload)
    assert (
        sum('resource "aws_cloudwatch_event_target"' in v for v in tree.values()) == 2
    )
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.parametrize("path", [None, "$.detail.customerId"])
def test_stream_targets_validate(path, tmp_path):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "partition_key_path": path,
        "input": '{"job":"daily"}',
    }
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
