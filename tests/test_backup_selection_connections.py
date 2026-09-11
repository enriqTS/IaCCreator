"""Backup selections stay plan-owned and resource-scoped."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.backup import BackupSelectionConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.backup_selection import BACKUP_OUTPUTS
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


def architecture(service=ServiceType.EBS):
    return connection_architecture(
        resolve_spec(ServiceType.BACKUP, service, "backs_up", {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


@pytest.mark.parametrize("service", BACKUP_OUTPUTS)
def test_plan_owned_selection_uses_exact_resource_arn(service):
    payload = architecture(service)
    tree = CodeGenerator().generate(project(payload))
    selection = tree[
        "connection-check/modules/storage/backup/source-resource/selection_target-resource.tf"
    ]
    assert "plan_id = aws_backup_plan.source-resource.id" in selection
    assert "resources = [var.backup_target-resource_arn]" in selection
    assert "iam_role_arn = var.backup_target-resource_role_arn" in selection
    assert (
        f"module.target-resource.{BACKUP_OUTPUTS[service]}"
        in tree["connection-check/environments/dev/main.tf"]
    )
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert preview.resources[0].module == "source-resource"
    assert preview.resources[0].resource_type == "aws_backup_selection"
    assert not preview.iam and "external backup role" in preview.issues[0].message


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"role_arn": ""},
        {"role_arn": "arn:aws:iam::123456789012:user/backup"},
        {"role_arn": "admin"},
    ],
)
def test_backup_role_is_explicit_and_typed(config):
    with pytest.raises(ValidationError):
        BackupSelectionConfig(**config)


def test_conflicting_roles_for_same_selection_are_rejected():
    payload = architecture()
    second = deepcopy(payload["connections"][0])
    second["connection_config"]["role_arn"] = "arn:aws:iam::123456789012:role/other"
    payload["connections"].append(second)
    with pytest.raises(InvalidConnectionConfigError, match="one backup service role"):
        CodeGenerator().generate(project(payload))


def mixed_architecture():
    payload = architecture()
    for index, service in enumerate(list(BACKUP_OUTPUTS)[1:]):
        extra = architecture(service)
        resource = extra["resources"][1]
        name = f"target-{index}"
        resource.update(name=name, id=name)
        connection = extra["connections"][0]
        connection.update(target=name, target_id=name)
        payload["resources"].append(resource)
        payload["connections"].append(connection)
    return payload


def test_all_resource_types_and_duplicate_selections_are_deterministic():
    payload = mixed_architecture()
    tree = CodeGenerator().generate(project(payload))
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert CodeGenerator().generate(project(payload)) == tree
    assert sum(
        text.count('resource "aws_backup_selection"') for text in tree.values()
    ) == len(BACKUP_OUTPUTS)
    assert not any('resource "aws_iam_role"' in text for text in tree.values())


@needs_terraform
def test_mixed_backup_project_validates(tmp_path):
    _write_tree(tmp_path, CodeGenerator().generate(project(mixed_architecture())))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
