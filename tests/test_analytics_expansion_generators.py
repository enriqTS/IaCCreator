"""Tests for the Phase 3 analytics service generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.datazone_config import DataZoneConfig
from app.models.input_models.lake_formation_config import LakeFormationConfig
from app.models.input_models.quicksight_config import QuickSightConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog

ANALYTICS_CONFIGS = {
    ServiceType.QUICKSIGHT: QuickSightConfig(),
    ServiceType.LAKE_FORMATION: LakeFormationConfig(),
    ServiceType.DATAZONE: DataZoneConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), ANALYTICS_CONFIGS.items())
def test_analytics_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="analytics_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_lake_formation_custom_role_uses_module_input() -> None:
    instance = ResourceInstanceIR(
        name="lake",
        service_type=ServiceType.LAKE_FORMATION,
        config=LakeFormationConfig(
            use_service_linked_role=False,
            role_arn="arn:aws:iam::123456789012:role/lake",
        ),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.LAKE_FORMATION].generate_resource_tf(instance)
    assert "role_arn = var.role_arn" in hcl
    assert "arn:aws:iam" not in hcl


def test_datazone_optional_encryption_uses_variable() -> None:
    instance = ResourceInstanceIR(
        name="catalog",
        service_type=ServiceType.DATAZONE,
        config=DataZoneConfig(
            kms_key_identifier="arn:aws:kms:us-east-1:123456789012:key/example"
        ),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.DATAZONE].generate_resource_tf(instance)
    assert "kms_key_identifier = var.kms_key_identifier" in hcl


def test_legacy_kinesis_data_analytics_is_retired() -> None:
    metadata = build_service_catalog()[ServiceType.KINESIS_DATA_ANALYTICS]
    assert metadata.lifecycle.value == "retired"
    assert not metadata.capabilities.terraform
