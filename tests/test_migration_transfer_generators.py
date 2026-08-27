import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.datasync_config import DataSyncConfig
from app.models.input_models.transfer_family_config import TransferFamilyConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog

SERVICE_CONFIGS = {
    ServiceType.DATASYNC: DataSyncConfig(),
    ServiceType.TRANSFER_FAMILY: TransferFamilyConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_migration_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="migration_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_datasync_uses_location_arn_inputs() -> None:
    instance = ResourceInstanceIR(
        name="transfer", service_type=ServiceType.DATASYNC, config=DataSyncConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.DATASYNC].generate_resource_tf(instance)
    assert "source_location_arn = var.source_location_arn" in hcl
    assert "destination_location_arn = var.destination_location_arn" in hcl


@pytest.mark.parametrize(
    "service_type",
    [
        ServiceType.APPLICATION_MIGRATION_SERVICE,
        ServiceType.MAINFRAME_MODERNIZATION,
        ServiceType.MIGRATION_HUB,
    ],
)
def test_migration_services_without_provider_resources_are_capabilities(
    service_type,
) -> None:
    metadata = build_service_catalog()[service_type]
    assert metadata.classification.value == "capability"
    assert not metadata.capabilities.terraform
