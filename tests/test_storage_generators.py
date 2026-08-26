"""Tests for foundational storage service generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.backup_config import BackupConfig
from app.models.input_models.ebs_config import EbsConfig
from app.models.input_models.efs_config import EfsConfig
from app.models.ir_models import ResourceInstanceIR

STORAGE_CONFIGS = {
    ServiceType.EBS: EbsConfig(),
    ServiceType.EFS: EfsConfig(),
    ServiceType.BACKUP: BackupConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), STORAGE_CONFIGS.items())
def test_storage_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="storage_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_ebs_gp3_emits_performance_settings() -> None:
    instance = ResourceInstanceIR(
        name="data", service_type=ServiceType.EBS, config=EbsConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.EBS].generate_resource_tf(instance)
    assert "iops" in hcl
    assert "throughput" in hcl


def test_efs_mount_targets_reference_file_system() -> None:
    instance = ResourceInstanceIR(
        name="shared",
        service_type=ServiceType.EFS,
        config=EfsConfig(subnet_ids=["subnet-123"], security_group_ids=["sg-123"]),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.EFS].generate_resource_tf(instance)
    assert 'resource "aws_efs_mount_target"' in hcl
    assert "aws_efs_file_system.shared.id" in hcl
    assert "toset(var.subnet_ids)" in hcl


def test_backup_plan_references_generated_vault() -> None:
    instance = ResourceInstanceIR(
        name="daily", service_type=ServiceType.BACKUP, config=BackupConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.BACKUP].generate_resource_tf(instance)
    assert 'resource "aws_backup_plan"' in hcl
    assert "aws_backup_vault.daily.name" in hcl
