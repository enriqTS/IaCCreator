import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.iot_core_config import IotCoreConfig
from app.models.input_models.iot_device_management_config import (
    IotDeviceManagementConfig,
)
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog

SERVICE_CONFIGS = {
    ServiceType.IOT_CORE: IotCoreConfig(),
    ServiceType.IOT_DEVICE_MANAGEMENT: IotDeviceManagementConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_iot_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="iot_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_iot_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


@pytest.mark.parametrize(
    "service_type",
    [
        ServiceType.IOT_GREENGRASS,
        ServiceType.IOT_DEVICE_DEFENDER,
        ServiceType.IOT_EVENTS,
        ServiceType.IOT_SITEWISE,
        ServiceType.IOT_TWINMAKER,
        ServiceType.IOT_FLEETWISE,
    ],
)
def test_iot_services_without_provider_resources_are_capabilities(service_type) -> None:
    metadata = build_service_catalog()[service_type]
    assert metadata.classification.value == "capability"
    assert not metadata.capabilities.terraform


def test_iot_analytics_is_deprecated() -> None:
    metadata = build_service_catalog()[ServiceType.IOT_ANALYTICS]
    assert metadata.lifecycle.value == "deprecated"
    assert not metadata.capabilities.terraform
