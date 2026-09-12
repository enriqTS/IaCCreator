"""S3 replication preserves one owner and versioning dependencies."""

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
    return connection_architecture(
        resolve_spec(ServiceType.S3, ServiceType.S3, "replicates_to", {})
    )


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


def test_replication_is_source_owned_and_waits_for_both_versioning_resources():
    tree = generate(architecture())
    source = "connection-check/modules/storage/s3/source-resource/"
    target = "connection-check/modules/storage/s3/target-resource/"
    assert (
        'resource "aws_s3_bucket_replication_configuration"'
        in tree[source + "replication.tf"]
    )
    assert (
        "depends_on = [aws_s3_bucket_versioning.source-resource_versioning]"
        in tree[source + "replication.tf"]
    )
    assert (
        "depends_on = [aws_s3_bucket_versioning.target-resource_versioning]"
        in tree[target + "outputs.tf"]
    )
    main = tree["connection-check/environments/dev/main.tf"]
    assert main.count('versioning_enabled = "Enabled"') == 2
    assert "module.target-resource.replication_bucket_arn" in main


def mixed_architecture():
    payload = architecture()
    source = payload["resources"][0]["config"]
    source["replication_destination_bucket"] = "arn:aws:s3:::external-replica"
    second = deepcopy(payload["resources"][1])
    second.update(name="other", id="other", provider_region="us-west-2")
    payload["resources"].append(second)
    extra = deepcopy(payload["connections"][0])
    extra.update(target="other", target_id="other")
    extra["connection_config"]["prefix"] = "data/"
    payload["connections"].append(extra)
    return payload


def test_multi_destination_replication_and_external_fallback_are_deterministic():
    payload = mixed_architecture()
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    text = "\n".join(tree.values())
    assert text.count('resource "aws_s3_bucket_replication_configuration"') == 1
    replication = tree[
        "connection-check/modules/storage/s3/source-resource/replication.tf"
    ]
    assert replication.count("rule {") == 3
    assert "var.replication_destination_bucket" in replication
    assert 'prefix = "data/"' in replication


def test_conflicting_replication_roles_rejected():
    payload = mixed_architecture()
    payload["connections"][1]["connection_config"]["role_arn"] = (
        "arn:aws:iam::123456789012:role/other"
    )
    with pytest.raises(InvalidConnectionConfigError, match="same role"):
        generate(payload)


def test_kms_source_requires_replica_key():
    payload = architecture()
    payload["resources"][0]["config"]["sse_algorithm"] = "aws:kms"
    with pytest.raises(InvalidConnectionConfigError, match="destination KMS key"):
        generate(payload)


def encrypted_architecture():
    payload = architecture()
    payload["resources"].append(
        {
            "name": "key",
            "service_type": "kms",
            "config": {"description": "Replication key"},
        }
    )
    for target in ["source-resource", "target-resource"]:
        payload["connections"].append(
            {"source": "key", "target": target, "connection_type": "encrypts"}
        )
    return payload


def test_kms_replication_uses_managed_key_reference():
    tree = generate(encrypted_architecture())
    text = "\n".join(tree.values())
    assert "replica_kms_key_id = var.replica_target-resource_" in text
    assert "sse_kms_encrypted_objects {" in text
    assert "module.key.key_arn" in tree["connection-check/environments/dev/main.tf"]


@pytest.mark.parametrize("builder", [mixed_architecture, encrypted_architecture])
@needs_terraform
def test_replication_projects_validate_without_cycles(tmp_path, builder):
    _write_tree(tmp_path, generate(builder()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
