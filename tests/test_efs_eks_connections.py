"""EKS static storage exports preserve claim identity and least-privilege node access."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.eks_efs_manifests import storage_manifests, workload_mount
from app.models.connection_configs.efs import EfsEksMountConfig
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
        resolve_spec(ServiceType.EFS, ServiceType.EKS, "mounts", {})
    )


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


@given(st.sampled_from(["read", "write"]), st.sampled_from(["default", "application"]))
def test_static_claim_binding_and_read_only_flags(access, namespace):
    config = EfsEksMountConfig(
        access=access,
        namespace=namespace,
        node_role_arn="arn:aws:iam::123456789012:role/workers",
    )
    pv, pvc = storage_manifests("efs_123", config)
    assert pv["spec"]["claimRef"] == pvc["metadata"]
    assert pvc["spec"]["volumeName"] == pv["metadata"]["name"]
    assert pv["spec"]["persistentVolumeReclaimPolicy"] == "Retain"
    assert pv["spec"]["accessModes"] == pvc["spec"]["accessModes"] == ["ReadWriteMany"]
    assert pv["spec"]["mountOptions"][:2] == ["tls", "iam"]
    assert pv["spec"]["csi"]["readOnly"] == (access == "read")
    assert workload_mount("efs_123", config)["volumeMount"]["readOnly"] == (
        access == "read"
    )


def test_single_driver_and_static_permissions_aggregate():
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["claim_name"] = "other"
    other["connection_config"]["access"] = "write"
    payload["connections"].append(other)
    expected = generate(payload)
    text = "\n".join(expected.values())
    assert text.count('resource "aws_eks_addon"') == 1
    assert text.count('resource "aws_iam_role_policy"') == 1
    assert text.count('resource "aws_efs_access_point"') == 2
    assert "elasticfilesystem:CreateAccessPoint" not in text
    assert "elasticfilesystem:ClientWrite" in text
    assert "efs_storage_manifests" in text
    assert any(path.endswith("EFS-MOUNTS.md") for path in expected)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


def test_existing_csi_driver_is_preserved():
    payload = architecture()
    payload["resources"][1]["config"]["manage_efs_csi_driver"] = False
    text = "\n".join(generate(payload).values())
    assert 'resource "aws_eks_addon"' not in text
    assert "efs_storage_manifests" in text


def test_conflicting_claim_bindings_are_rejected():
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["local_mount_path"] = "/mnt/other"
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError, match="one EFS mount"):
        generate(payload)


@needs_terraform
def test_storage_exports_validate_without_cycles(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)


def test_workload_path_changes_preserve_claim_storage():
    payload = architecture()
    before = generate(payload)
    payload["connections"][0]["connection_config"]["local_mount_path"] = "/mnt/changed"
    after = generate(payload)
    for path, content in before.items():
        if "/efs/source-resource/" in path:
            assert after[path] == content
