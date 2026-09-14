"""EC2 bootstrap mounts compose with user scripts and runtime secret credentials."""

import base64
import json
import subprocess
from copy import deepcopy
from pathlib import Path

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
        resolve_spec(ServiceType.EFS, ServiceType.EC2, "mounts", {})
    )
    payload["resources"][1]["config"]["user_data"] = (
        '#!/bin/bash\nprintf "%s" "${HOSTNAME}"\n'
    )
    return payload


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


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
            "connection_type": "reads_secret",
        }
    )
    return payload


def test_mounts_and_secrets_share_one_role_and_profile():
    payload = mixed_architecture()
    expected = generate(payload)
    text = "\n".join(expected.values())
    assert text.count('resource "aws_iam_role"') == 1
    assert text.count('resource "aws_iam_instance_profile"') == 1
    assert "aws_iam_role_policy.efs_mounts" in text
    assert "aws_iam_role_policy.runtime_secrets" in text
    assert "user_data_replace_on_change = true" in text
    assert "$${HOSTNAME}" in text
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


@pytest.mark.parametrize(
    "user_data",
    ["#cloud-config\npackages: []", "MIME-Version: 1.0", "#!/usr/bin/python\nprint(1)"],
)
def test_non_shell_user_data_is_rejected(user_data):
    payload = architecture()
    payload["resources"][1]["config"]["user_data"] = user_data
    with pytest.raises(InvalidConnectionConfigError, match="shell user data"):
        generate(payload)


@needs_terraform
@pytest.mark.parametrize("install", [False, True])
def test_rendered_bootstrap_has_valid_shell_and_iam_mounts(tmp_path, install):
    template = Path("app/generators/templates/efs_bootstrap.sh.tftpl").resolve()
    expression = f'templatefile({json.dumps(str(template))}, {{ mounts = [{{filesystem_id="fs-123", access_point_id="fsap-123", path="/mnt/data", read_only=true}}], install_helper={str(install).lower()}, user_script="" }})'
    result = subprocess.run(
        ["terraform", "console", "-no-color"],
        cwd=tmp_path,
        input=f"base64encode({expression})",
        capture_output=True,
        text=True,
        check=True,
    )
    script = base64.b64decode(json.loads(result.stdout)).decode()
    subprocess.run(["bash", "-n"], input=script, text=True, check=True)
    assert "tls,iam,accesspoint=fsap-123,ro" in script
    assert ("dnf install" in script) == install


@needs_terraform
def test_mixed_mount_project_validates_without_cycles(tmp_path):
    _write_tree(tmp_path, generate(mixed_architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
