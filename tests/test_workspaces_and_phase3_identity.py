"""Tests for WorkSpaces generation and Phase 3 identity decisions."""

from app.generators.registry import GENERATOR_REGISTRY
from app.models.editor_models import ServiceClassification
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.workspaces_config import WorkSpacesConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog
from scripts.audit_service_catalog import read_frontend_catalog


def test_workspaces_generator_emits_typed_terraform() -> None:
    instance = ResourceInstanceIR(
        name="developer_desktop",
        service_type=ServiceType.WORKSPACES,
        config=WorkSpacesConfig(
            directory_id="d-123", bundle_id="wsb-123", user_name="developer"
        ),
    )
    generator = GENERATOR_REGISTRY[ServiceType.WORKSPACES]
    hcl = generator.generate_resource_tf(instance)
    assert 'resource "aws_workspaces_workspace"' in hcl
    assert "directory_id = var.directory_id" in hcl
    assert "d-123" not in hcl
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[ServiceType.WORKSPACES].has_terraform_schema()


def test_workspaces_is_separate_from_family_composite() -> None:
    catalog = build_service_catalog()
    assert (
        catalog[ServiceType.WORKSPACES].classification == ServiceClassification.RESOURCE
    )
    assert catalog[ServiceType.WORKSPACES].capabilities.terraform
    assert (
        catalog[ServiceType.WORKSPACES_FAMILY].classification
        == ServiceClassification.COMPOSITE
    )
    assert not catalog[ServiceType.WORKSPACES_FAMILY].capabilities.terraform


def test_fargate_has_one_catalog_icon_and_remains_a_capability() -> None:
    typed, _ = read_frontend_catalog()
    assert len(typed[ServiceType.FARGATE.value]) == 1
    metadata = build_service_catalog()[ServiceType.FARGATE]
    assert metadata.classification == ServiceClassification.CAPABILITY
    assert not metadata.capabilities.terraform


def test_kinesis_data_streams_retains_compatibility_identity() -> None:
    catalog = build_service_catalog()
    assert catalog[ServiceType.KINESIS].capabilities.terraform
    assert not catalog[ServiceType.KINESIS_DATA_STREAMS].capabilities.terraform
