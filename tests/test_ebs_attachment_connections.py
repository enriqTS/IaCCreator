"""EBS attachments preserve device uniqueness and managed zone placement."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.storage import EbsAttachmentConfig
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
        resolve_spec(ServiceType.EBS, ServiceType.EC2, "attaches", {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def test_attachment_is_volume_owned_and_uses_instance_zone():
    payload = architecture()
    ir = project(payload)
    tree = CodeGenerator().generate(ir)
    hcl = tree["connection-check/modules/storage/ebs/source-resource/attachment.tf"]
    assert 'device_name = "/dev/sdf"' in hcl
    assert "volume_id = aws_ebs_volume.source-resource.id" in hcl
    assert "instance_id = var.attached_instance_id" in hcl
    main = tree["connection-check/environments/dev/main.tf"]
    assert "availability_zone = module.target-resource.availability_zone" in main
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert preview.resources[0].module == "source-resource"
    assert preview.resources[0].resource_type == "aws_volume_attachment"
    assert preview.issues and not preview.iam


@pytest.mark.parametrize(
    "device", ["/dev/sda", "/dev/sda1", "sdf", "/dev/nvme0n1", "invalid"]
)
def test_invalid_device_names_rejected(device):
    with pytest.raises(ValidationError):
        EbsAttachmentConfig(device_name=device)


def multiple_volumes():
    payload = architecture()
    payload["resources"].append(
        {"name": "second", "service_type": "ebs", "config": {"size": 30}}
    )
    payload["connections"].append(
        {
            "source": "second",
            "target": "target-resource",
            "connection_type": "attaches",
            "connection_config": {"device_name": "/dev/sdg"},
        }
    )
    return payload


def test_distinct_volumes_and_duplicates_are_deterministic():
    payload = multiple_volumes()
    expected = CodeGenerator().generate(project(payload))
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert CodeGenerator().generate(project(payload)) == expected
    assert (
        sum(
            text.count('resource "aws_volume_attachment"') for text in expected.values()
        )
        == 2
    )


@pytest.mark.parametrize("device", ["/dev/sdf", "/dev/xvdf"])
def test_device_collisions_rejected_including_linux_aliases(device):
    payload = multiple_volumes()
    payload["connections"][1]["connection_config"]["device_name"] = device
    with pytest.raises(InvalidConnectionConfigError, match="one volume"):
        CodeGenerator().generate(project(payload))


def test_multi_attach_rejected():
    payload = architecture()
    second = deepcopy(payload["resources"][1])
    second.update(name="other", id="other")
    payload["resources"].append(second)
    payload["connections"].append(
        {"source": "source-resource", "target": "other", "connection_type": "attaches"}
    )
    with pytest.raises(InvalidConnectionConfigError, match="one instance/device"):
        CodeGenerator().generate(project(payload))


@needs_terraform
def test_multi_volume_project_validates(tmp_path):
    _write_tree(tmp_path, CodeGenerator().generate(project(multiple_volumes())))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
