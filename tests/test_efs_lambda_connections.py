"""EFS Lambda mounts own access points and enforce placement prerequisites."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.storage import EfsLambdaMountConfig
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


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.EFS, ServiceType.LAMBDA, "mounts", {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


@pytest.mark.parametrize("access", ["read", "write"])
def test_access_point_and_lambda_configuration_with_scoped_permissions(access):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"access": access}
    tree = CodeGenerator().generate(project(payload))
    point = tree[
        "connection-check/modules/storage/efs/source-resource/target_resource_access_point.tf"
    ]
    assert "uid = 1000" in point and "gid = 1000" in point
    assert 'path = "/target-resource"' in point
    assert "file_system_id = aws_efs_file_system.source-resource.id" in point
    function = tree["connection-check/modules/compute/lambda/target-resource/lambda.tf"]
    assert "file_system_config {" in function
    assert "arn = var.file_system_arn" in function
    policy = json.loads(
        tree["connection-check/iam-policies/target-resource-policy.json"]
    )
    statements = [
        item
        for item in policy["Statement"]
        if "elasticfilesystem:ClientMount" in item["Action"]
    ]
    assert statements[0]["Resource"] == "${aws_efs_file_system.source-resource.arn}"
    assert ("elasticfilesystem:ClientWrite" in statements[0]["Action"]) == (
        access == "write"
    )
    outputs = tree["connection-check/modules/storage/efs/source-resource/outputs.tf"]
    assert "depends_on = [aws_efs_mount_target.source-resource]" in outputs
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert preview.resources[0].module == "source-resource"
    assert preview.issues


@pytest.mark.parametrize(
    "config",
    [
        {"local_mount_path": "/tmp/efs"},
        {"root_directory": "/"},
        {"uid": 0},
        {"gid": -1},
        {"access": "root"},
    ],
)
def test_mount_config_validation(config):
    with pytest.raises(ValidationError):
        EfsLambdaMountConfig(**config)


@pytest.mark.parametrize(
    "index, field",
    [(0, "subnet_ids"), (1, "vpc_subnet_ids"), (1, "vpc_security_group_ids")],
)
def test_missing_network_placement_is_rejected(index, field):
    payload = architecture()
    payload["resources"][index]["config"].pop(field)
    with pytest.raises(InvalidConnectionConfigError, match="requires"):
        CodeGenerator().generate(project(payload))


def test_multiple_bindings_for_one_function_are_rejected():
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"] = {"local_mount_path": "/mnt/other"}
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="one EFS"):
        CodeGenerator().generate(project(payload))


def test_multiple_functions_share_filesystem_without_resource_collisions():
    payload = architecture()
    second = deepcopy(payload["resources"][1])
    second.update(name="second", id="second")
    payload["resources"].append(second)
    payload["connections"].append(
        {"source": "source-resource", "target": "second", "connection_type": "mounts"}
    )
    expected = CodeGenerator().generate(project(payload))
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert CodeGenerator().generate(project(payload)) == expected
    assert (
        sum(text.count('resource "aws_efs_access_point"') for text in expected.values())
        == 2
    )


@needs_terraform
def test_mount_project_with_managed_subnet_validates(tmp_path):
    payload = architecture()
    payload["resources"][0]["config"]["subnet_ids"] = []
    payload["resources"].append(
        {
            "name": "subnet",
            "service_type": "subnet",
            "config": {"vpc_id": "vpc-12345678", "cidr_block": "10.0.0.0/24"},
        }
    )
    payload["connections"].append(
        {"source": "subnet", "target": "source-resource", "connection_type": "places"}
    )
    tree = CodeGenerator().generate(project(payload))
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
