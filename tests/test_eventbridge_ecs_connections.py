"""EventBridge ECS targets bind tasks, networking, and invocation permissions."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.eventbridge_ecs import EventBridgeEcsConfig
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
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.ECS, None, {})
    )


def test_target_uses_native_task_network_and_scoped_role():
    tree = generate(architecture())
    target = next(v for k, v in tree.items() if "/ecs_" in k)
    assert '"ecs:RunTask"' in target
    assert '"iam:PassRole"' in target
    assert "ecs:cluster" in target
    assert "iam:PassedToService" in target
    assert "ecs_target" in target
    assert "task_definition_arn = var.ecs_" in target
    assert 'launch_type = "FARGATE"' in target
    assert "subnets = var.ecs_" in target
    assert "module.target-resource.task_definition_arn" in "\n".join(tree.values())
    assert "task_role_arn = aws_iam_role.target-resource_role.arn" in "\n".join(
        tree.values()
    )
    assert generate(architecture()) == tree


def test_missing_network_and_wrong_launch_type_rejected():
    for change in (
        {"subnet_ids": []},
        {"subnet_ids": ["managed-by-connection"]},
        {"ecs_launch_type": "EC2"},
    ):
        payload = architecture()
        payload["resources"][1]["config"].update(change)
        with pytest.raises(InvalidConnectionConfigError):
            generate(payload)


@pytest.mark.parametrize("count", [0, 11, True])
def test_invalid_task_count_rejected(count):
    with pytest.raises(ValidationError):
        EventBridgeEcsConfig(task_count=count)


def test_target_id_conflict_rejects_different_task_counts():
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["task_count"] = 2
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_managed_subnet_is_shared_with_service_in_either_order():
    payload = architecture()
    payload["resources"][1]["config"]["subnet_ids"] = []
    placement = connection_architecture(
        resolve_spec(ServiceType.SUBNET, ServiceType.ECS, "places", {})
    )
    subnet = placement["resources"][0]
    subnet.update(id="subnet", name="managed-subnet")
    payload["resources"].append(subnet)
    connection = placement["connections"][0]
    connection.update(source="managed-subnet", source_id="subnet")
    payload["connections"].append(connection)
    expected = generate(payload)
    assert "module.managed-subnet.subnet_id" in "\n".join(expected.values())
    payload["connections"].reverse()
    assert generate(payload) == expected


@needs_terraform
def test_ecs_target_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
