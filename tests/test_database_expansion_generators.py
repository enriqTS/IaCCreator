"""Tests for the Phase 3 database service generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.dms_config import DmsConfig
from app.models.input_models.keyspaces_config import KeyspacesConfig
from app.models.input_models.memorydb_config import MemoryDbConfig
from app.models.ir_models import ResourceInstanceIR

DATABASE_CONFIGS = {
    ServiceType.DATABASE_MIGRATION_SERVICE: DmsConfig(),
    ServiceType.KEYSPACES: KeyspacesConfig(),
    ServiceType.MEMORYDB: MemoryDbConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), DATABASE_CONFIGS.items())
def test_database_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="database_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_dms_subnet_group_is_owned_by_replication_module() -> None:
    instance = ResourceInstanceIR(
        name="migration",
        service_type=ServiceType.DATABASE_MIGRATION_SERVICE,
        config=DmsConfig(subnet_ids=["subnet-1", "subnet-2"]),
    )
    hcl = GENERATOR_REGISTRY[
        ServiceType.DATABASE_MIGRATION_SERVICE
    ].generate_resource_tf(instance)
    assert 'resource "aws_dms_replication_subnet_group"' in hcl
    assert "aws_dms_replication_subnet_group.migration.id" in hcl


def test_memorydb_subnet_group_is_referenced_by_cluster() -> None:
    instance = ResourceInstanceIR(
        name="cache",
        service_type=ServiceType.MEMORYDB,
        config=MemoryDbConfig(subnet_ids=["subnet-1"]),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.MEMORYDB].generate_resource_tf(instance)
    assert 'resource "aws_memorydb_subnet_group"' in hcl
    assert "aws_memorydb_subnet_group.cache.name" in hcl


def test_keyspaces_name_uses_module_variable() -> None:
    instance = ResourceInstanceIR(
        name="events", service_type=ServiceType.KEYSPACES, config=KeyspacesConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.KEYSPACES].generate_resource_tf(instance)
    assert "name = var.keyspace_name" in hcl
