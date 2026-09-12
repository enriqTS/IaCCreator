"""DataSync S3 locations are reusable resources with explicit transfer directions."""

from copy import deepcopy

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
        resolve_spec(
            ServiceType.DATASYNC_S3_LOCATION, ServiceType.S3, "uses_bucket", {}
        )
    )
    payload["resources"][0]["config"].update(access="read", subdirectory="/incoming/")
    payload["resources"] += [
        {
            "name": "destination",
            "service_type": "datasync-s3-location",
            "config": {
                "bucket_access_role_arn": "arn:aws:iam::123456789012:role/datasync/destination",
                "access": "write",
                "subdirectory": "/copied/",
            },
        },
        {
            "name": "output",
            "service_type": "s3",
            "config": {"bucket_prefix": "output-"},
        },
        {
            "name": "transfer",
            "service_type": "datasync",
            "config": {"task_name": "copy"},
        },
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Transfer encryption"},
        },
    ]
    payload["connections"] += [
        {"source": "destination", "target": "output", "connection_type": "uses_bucket"},
        {
            "source": "transfer",
            "target": "source-resource",
            "connection_type": "reads_from",
        },
        {"source": "transfer", "target": "destination", "connection_type": "writes_to"},
        {"source": "key", "target": "output", "connection_type": "encrypts"},
    ]
    return payload


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_locations_and_directional_permissions():
    tree = generate(architecture())
    text = "\n".join(tree.values())
    assert text.count('resource "aws_datasync_location_s3"') == 2
    assert "module.source-resource.location_arn" in text
    assert "module.destination.location_arn" in text
    source = next(
        value
        for path, value in tree.items()
        if "/source-resource/location_access.tf" in path
    )
    destination = next(
        value
        for path, value in tree.items()
        if "/destination/location_access.tf" in path
    )
    assert '"s3:PutObject"' not in source
    assert '"s3:PutObject"' in destination
    assert '"s3:DeleteObject"' in destination
    assert '"kms:GenerateDataKey"' in destination
    assert "managed-by-connection" not in text


def test_duplicates_and_order_are_stable():
    payload = architecture()
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


def test_read_only_destination_is_rejected():
    payload = architecture()
    payload["resources"][2]["config"]["access"] = "read"
    with pytest.raises(InvalidConnectionConfigError, match="write access"):
        generate(payload)


def test_same_location_in_both_directions_is_rejected():
    payload = architecture()
    payload["connections"][3]["target"] = "source-resource"
    with pytest.raises(InvalidConnectionConfigError, match="distinct location"):
        generate(payload)


@needs_terraform
def test_managed_transfer_validates_without_cycles(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
