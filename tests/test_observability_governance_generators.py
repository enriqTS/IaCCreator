import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.aws_config_config import AwsConfigConfig
from app.models.input_models.cloudtrail_config import CloudTrailConfig
from app.models.input_models.fault_injection_simulator_config import (
    FaultInjectionSimulatorConfig,
)
from app.models.input_models.managed_grafana_config import ManagedGrafanaConfig
from app.models.input_models.managed_prometheus_config import ManagedPrometheusConfig
from app.models.input_models.organizations_config import OrganizationsConfig
from app.models.input_models.systems_manager_config import SystemsManagerConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog

SERVICE_CONFIGS = {
    ServiceType.CLOUDTRAIL: CloudTrailConfig(),
    ServiceType.AWS_CONFIG: AwsConfigConfig(),
    ServiceType.SYSTEMS_MANAGER: SystemsManagerConfig(),
    ServiceType.ORGANIZATIONS: OrganizationsConfig(),
    ServiceType.MANAGED_GRAFANA: ManagedGrafanaConfig(),
    ServiceType.MANAGED_PROMETHEUS: ManagedPrometheusConfig(),
    ServiceType.FAULT_INJECTION_SIMULATOR: FaultInjectionSimulatorConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_governance_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="governance_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_aws_config_orders_recorder_delivery_and_status() -> None:
    instance = ResourceInstanceIR(
        name="configuration",
        service_type=ServiceType.AWS_CONFIG,
        config=AwsConfigConfig(),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.AWS_CONFIG].generate_resource_tf(instance)
    assert "aws_config_configuration_recorder.configuration" in hcl
    assert "aws_config_delivery_channel.configuration" in hcl
    assert 'resource "aws_config_configuration_recorder_status"' in hcl


def test_control_tower_remains_a_composite() -> None:
    metadata = build_service_catalog()[ServiceType.CONTROL_TOWER]
    assert metadata.classification.value == "composite"
    assert not metadata.capabilities.terraform
