"""Tests for CodeArtifact and X-Ray generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.codeartifact_config import CodeArtifactConfig
from app.models.input_models.xray_config import XRayConfig
from app.models.ir_models import ResourceInstanceIR

SERVICE_CONFIGS = {
    ServiceType.CODEARTIFACT: CodeArtifactConfig(),
    ServiceType.X_RAY: XRayConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="developer_service", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_codeartifact_repository_references_domain() -> None:
    instance = ResourceInstanceIR(
        name="packages",
        service_type=ServiceType.CODEARTIFACT,
        config=CodeArtifactConfig(upstream_repository_names=["shared"]),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.CODEARTIFACT].generate_resource_tf(instance)
    assert "aws_codeartifact_domain.packages.domain" in hcl
    assert "var.upstream_repository_names[0]" in hcl


def test_xray_insights_configuration_uses_variables() -> None:
    instance = ResourceInstanceIR(
        name="traces", service_type=ServiceType.X_RAY, config=XRayConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.X_RAY].generate_resource_tf(instance)
    assert "insights_enabled = var.insights_enabled" in hcl
    assert "notifications_enabled = var.notifications_enabled" in hcl
