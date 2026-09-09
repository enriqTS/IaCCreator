"""CloudTrail KMS policy ownership, aggregation, and dependency coverage."""

from copy import deepcopy

import pytest

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.hcl_assertions import assert_tree_parses


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.KMS, ServiceType.CLOUDTRAIL, "encrypts", {})
    )


@pytest.mark.parametrize("duplicate", [False, True])
def test_shared_key_policy_aggregates_trails_deterministically(duplicate):
    payload = architecture()
    trail = deepcopy(payload["resources"][1])
    trail.update(id="second", name="second-trail")
    trail["config"]["trail_name"] = "other-audit"
    payload["resources"].append(trail)
    connection = dict(
        payload["connections"][0], target="second-trail", target_id="second"
    )
    payload["connections"].append(connection)
    if duplicate:
        payload["connections"].append(dict(connection))
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    contribution = ConnectionProcessor().process_all(project)
    paths = [
        (resource.module, resource.filename) for resource in contribution.resources
    ]
    assert len(paths) == len(set(paths))
    policy = next(
        resource
        for resource in contribution.resources
        if resource.filename == "key_policy.tf"
    )
    assert policy.module == "source-resource"
    assert '"kms:GenerateDataKey*"' in policy.content
    assert '"kms:DescribeKey"' in policy.content
    assert '"kms:Decrypt"' not in policy.content
    assert '"aws:SourceArn" = var.cloudtrail_arns' in policy.content
    assert (
        '"kms:EncryptionContext:aws:cloudtrail:arn" = var.cloudtrail_arns'
        in policy.content
    )
    assert "EnableAccountPermissions" in policy.content
    tree = CodeGenerator().generate(project)
    assert_tree_parses(tree)
    payload["connections"].reverse()
    reversed_tree = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )
    assert dict(tree) == dict(reversed_tree)
    environment = tree["connection-check/environments/dev/main.tf"]
    assert (
        "cloudtrail_arns = [module.second-trail.encryption_trail_arn, module.target-resource.encryption_trail_arn]"
        in environment
    )
    assert (
        environment.count("kms_key_id = module.source-resource.cloudtrail_key_arn") == 2
    )


def test_preview_and_policy_dependency():
    project = IRBuilder().build(ArchitectureDescription.model_validate(architecture()))
    preview = ConnectionPreviewer().preview_all(project)[0]
    assert preview.issues == []
    assert [
        (resource.module, resource.resource_type) for resource in preview.resources
    ] == [("source-resource", "aws_kms_key_policy")]
    contribution = ConnectionProcessor().process_all(project)
    key_output = next(
        output for output in contribution.outputs if output.name == "cloudtrail_key_arn"
    )
    assert key_output.value == "aws_kms_key_policy.services.key_id"
    trail_output = next(
        output
        for output in contribution.outputs
        if output.name == "encryption_trail_arn"
    )
    assert "var.trail_name" in trail_output.value
    assert "aws_cloudtrail." not in trail_output.value


def test_two_keys_for_one_trail_are_rejected():
    payload = architecture()
    key = deepcopy(payload["resources"][0])
    key.update(id="second-key", name="second-key")
    payload["resources"].append(key)
    payload["connections"].append(
        dict(payload["connections"][0], source="second-key", source_id="second-key")
    )
    with pytest.raises(InvalidConnectionConfigError, match="only one KMS key"):
        CodeGenerator().generate(
            IRBuilder().build(ArchitectureDescription.model_validate(payload))
        )


@pytest.mark.parametrize(
    "key", [None, "arn:aws:kms:us-east-1:123456789012:key/external"]
)
def test_external_key_remains_usable(key):
    payload = architecture()
    payload["connections"] = []
    payload["resources"][1]["config"]["kms_key_id"] = key
    tree = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )
    resource = next(
        content for path, content in tree.items() if path.endswith("/cloudtrail.tf")
    )
    assert ("kms_key_id = var.kms_key_id" in resource) == (key is not None)
    assert not any(path.endswith("/key_policy.tf") for path in tree)


def test_shared_key_terraform_graph_has_no_cycle(tmp_path):
    from tests.test_generated_project_validates import (
        _init_args,
        _run_terraform,
        _write_tree,
        needs_terraform,
    )

    if needs_terraform.args[0]:
        pytest.skip("terraform binary not installed")
    payload = architecture()
    trail = deepcopy(payload["resources"][1])
    trail.update(id="second", name="second-trail")
    payload["resources"].append(trail)
    payload["connections"].append(
        dict(payload["connections"][0], target="second-trail", target_id="second")
    )
    tree = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)
