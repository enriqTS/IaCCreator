import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.ivs_config import IvsConfig
from app.models.input_models.media_live_config import MediaLiveConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog

SERVICE_CONFIGS = {
    ServiceType.MEDIA_LIVE: MediaLiveConfig(),
    ServiceType.INTERACTIVE_VIDEO_SERVICE: IvsConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_media_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="media_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_medialive_emits_each_allowlisted_cidr() -> None:
    config = MediaLiveConfig(allowed_cidrs=["10.0.0.0/8", "192.168.0.0/16"])
    instance = ResourceInstanceIR(
        name="live", service_type=ServiceType.MEDIA_LIVE, config=config
    )
    hcl = GENERATOR_REGISTRY[ServiceType.MEDIA_LIVE].generate_resource_tf(instance)
    assert "var.allowed_cidrs[0]" in hcl
    assert "var.allowed_cidrs[1]" in hcl


@pytest.mark.parametrize(
    "service_type",
    [
        ServiceType.MEDIA_CONNECT,
        ServiceType.MEDIA_CONVERT,
        ServiceType.MEDIA_PACKAGE,
        ServiceType.MEDIA_TAILOR,
        ServiceType.KINESIS_VIDEO_STREAMS,
    ],
)
def test_media_services_without_provider_resources_are_capabilities(
    service_type,
) -> None:
    metadata = build_service_catalog()[service_type]
    assert metadata.classification.value == "capability"
    assert not metadata.capabilities.terraform


def test_media_store_is_retired() -> None:
    metadata = build_service_catalog()[ServiceType.MEDIA_STORE]
    assert metadata.lifecycle.value == "retired"
    assert not metadata.capabilities.diagram
