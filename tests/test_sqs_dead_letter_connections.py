"""Dead-letter relationships compose without reciprocal Terraform dependencies."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.configs import SqsDeadLetterConfig
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
        resolve_spec(ServiceType.SQS, ServiceType.SQS, None, {})
    )


def add_source(payload, index):
    queue = deepcopy(payload["resources"][0])
    queue.update(id=f"source-{index}", name=f"source-{index}")
    queue["config"]["queue_name"] = f"source-{index}"
    payload["resources"].append(queue)
    link = deepcopy(payload["connections"][0])
    link.update(source=queue["name"], source_id=queue["id"])
    payload["connections"].append(link)


@given(count=st.integers(min_value=1, max_value=1000), fifo=st.booleans())
def test_redrive_is_scoped_native_and_destination_owned(count, fifo):
    payload = architecture()
    for resource in payload["resources"]:
        resource["config"].update(
            fifo_queue=fifo, queue_name=resource["name"] + (".fifo" if fifo else "")
        )
    payload["connections"][0]["connection_config"] = {"max_receive_count": count}
    tree = generate(payload)
    text = "\n".join(tree.values())
    redrive = next(
        v for k, v in tree.items() if k.endswith("/redrive_source-resource.tf")
    )
    assert f"maxReceiveCount = {count}" in redrive
    assert "deadLetterTargetArn = aws_sqs_queue.target-resource.arn" in redrive
    assert "queue_url = var.redrive_source-resource_url" in redrive
    assert (
        "var.redrive_source-resource_fifo_queue == aws_sqs_queue.target-resource.fifo_queue"
        in redrive
    )
    assert "account, partition, and region" in redrive
    allow = next(v for k, v in tree.items() if k.endswith("/redrive_allow.tf"))
    assert 'redrivePermission = "byQueue"' in allow
    assert "var.redrive_source-resource_arn" in allow
    assert "allowAll" not in text
    assert "aws_sqs_queue_policy" not in text
    assert "module.source-resource.redrive_url" in text
    assert "module.target-resource.redrive" not in text
    for path in tree:
        if path.endswith(("/redrive_source-resource.tf", "/redrive_allow.tf")):
            assert "/target-resource/" in path
    payload["connections"] *= 2
    assert generate(payload) == tree


@pytest.mark.parametrize("count", [0, 1001, -1, True, 1.5, "5"])
def test_receive_count_is_a_bounded_integer(count):
    with pytest.raises(ValidationError):
        SqsDeadLetterConfig(max_receive_count=count)


def test_default_and_schema_agree():
    assert SqsDeadLetterConfig().max_receive_count == 5
    field = SqsDeadLetterConfig.get_field_schema()[0]
    assert field.default == 5
    assert (field.validation.min, field.validation.max) == (1, 1000)


def test_fifo_mismatch_rejected():
    payload = architecture()
    payload["resources"][0]["config"].update(fifo_queue=True, queue_name="jobs.fifo")
    with pytest.raises(InvalidConnectionConfigError, match="both FIFO"):
        generate(payload)


@pytest.mark.parametrize("conflict", ["count", "destination", "cycle"])
def test_conflicting_or_cyclic_edges_rejected(conflict):
    payload = architecture()
    edge = deepcopy(payload["connections"][0])
    if conflict == "count":
        edge["connection_config"] = {"max_receive_count": 6}
    else:
        add_source(payload, 2)
        if conflict == "destination":
            edge.update(target="source-2", target_id="source-2")
        else:
            edge.update(
                source="target-resource",
                source_id="tgt",
                target="source-2",
                target_id="source-2",
            )
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError, match="one dead-letter|cycle"):
        generate(payload)


def test_shared_dead_letter_queue_limit_and_order_independence():
    payload = architecture()
    for index in range(9):
        add_source(payload, index)
    tree = generate(payload)
    assert (
        sum('resource "aws_sqs_queue_redrive_allow_policy"' in v for v in tree.values())
        == 1
    )
    assert (
        sum('resource "aws_sqs_queue_redrive_policy"' in v for v in tree.values()) == 10
    )
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    add_source(payload, 10)
    with pytest.raises(InvalidConnectionConfigError, match="at most 10"):
        generate(payload)


@needs_terraform
@pytest.mark.parametrize("topology", ["single", "shared", "chain"])
@pytest.mark.parametrize("fifo", [False, True])
def test_redrive_topologies_validate_without_cycles(topology, fifo, tmp_path):
    payload = architecture()
    if topology != "single":
        add_source(payload, 2)
        if topology == "chain":
            payload["connections"][1].update(
                source="target-resource",
                source_id="tgt",
                target="source-2",
                target_id="source-2",
            )
    for resource in payload["resources"]:
        resource["config"].update(
            fifo_queue=fifo, queue_name=resource["name"] + (".fifo" if fifo else "")
        )
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
