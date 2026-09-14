"""ECS mounts preserve container configuration and aggregate deterministically."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

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
        resolve_spec(ServiceType.EFS, ServiceType.ECS, "mounts", {})
    )


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


@given(st.sampled_from(["read", "write"]))
def test_native_volumes_use_tls_and_scoped_iam(access):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"access": access}
    text = "\n".join(generate(payload).values())
    assert 'transit_encryption = "ENABLED"' in text
    assert 'iam = "ENABLED"' in text
    assert "mountPoints = concat" in text
    assert '"elasticfilesystem:ClientMount"' in text
    assert ('"elasticfilesystem:ClientWrite"' in text) == (access == "write")
    assert "network_configuration {" in text
    assert "aws_efs_mount_target.source-resource" in text


def mixed_architecture():
    payload = architecture()
    payload["resources"].append(
        {
            "name": "secret",
            "service_type": ServiceType.SECRETS_MANAGER.value,
            "config": {"secret_name": "runtime"},
        }
    )
    payload["connections"].append(
        {
            "source": "target-resource",
            "target": "secret",
            "connection_type": "injects_secret",
        }
    )
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {"local_mount_path": "/mnt/other", "access": "write"}
    payload["connections"].append(other)
    return payload


def test_mounts_compose_with_secrets_and_duplicates():
    payload = mixed_architecture()
    expected = generate(payload)
    text = "\n".join(expected.values())
    assert "runtime_secrets" in text and "local.efs_mounts" in text
    assert text.count('resource "aws_efs_access_point"') == 2
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


@pytest.mark.parametrize("path", ["/mnt/efs", "/mnt/efs/nested"])
def test_conflicting_mount_paths_are_rejected(path):
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {"local_mount_path": path, "access": "write"}
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@needs_terraform
def test_mounts_with_secrets_validate_without_cycles(tmp_path):
    _write_tree(tmp_path, generate(mixed_architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)


@needs_terraform
def test_container_transform_preserves_external_mounts_and_secrets(tmp_path):
    import json
    import subprocess

    from app.generators.ecs_efs import add_efs_task_attributes
    from app.generators.ecs_secrets import secret_task_attributes
    from app.generators.hcl_renderer import HCLRenderer

    containers = [
        {
            "name": "app",
            "image": "image",
            "mountPoints": [
                {
                    "sourceVolume": "external",
                    "containerPath": "/other",
                    "readOnly": False,
                }
            ],
            "environment": [{"name": "KEEP", "value": "yes"}],
            "secrets": [{"name": "OLD", "valueFrom": "external-secret"}],
        }
    ]
    renderer = HCLRenderer()
    content = renderer.render_variable(
        "container_definitions", "string", "Containers", default=json.dumps(containers)
    )
    content += (
        "locals {\n  efs_mounts = "
        + renderer.render_expression(
            [
                {
                    "name": "managed",
                    "container": "app",
                    "path": "/mnt/data",
                    "read_only": True,
                }
            ]
        )
        + "\n  runtime_secrets = "
        + renderer.render_expression(
            [{"name": "NEW", "container": "app", "valueFrom": "managed-secret"}]
        )
        + "\n}\n"
    )
    (tmp_path / "main.tf").write_text(content)
    attrs = secret_task_attributes("app")
    add_efs_task_attributes(attrs)
    result = subprocess.run(
        ["terraform", "console", "-no-color"],
        cwd=tmp_path,
        input=str(attrs["container_definitions"]),
        capture_output=True,
        text=True,
        check=True,
    )
    transformed = json.loads(json.loads(result.stdout))[0]
    assert transformed["environment"] == containers[0]["environment"]
    assert transformed["mountPoints"][0] == containers[0]["mountPoints"][0]
    assert transformed["mountPoints"][1] == {
        "sourceVolume": "managed",
        "containerPath": "/mnt/data",
        "readOnly": True,
    }
    assert transformed["secrets"] == [
        {"name": "OLD", "valueFrom": "external-secret"},
        {"name": "NEW", "valueFrom": "managed-secret"},
    ]
