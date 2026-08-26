import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.comprehend_config import ComprehendConfig
from app.models.input_models.kendra_config import KendraConfig
from app.models.input_models.lex_config import LexConfig
from app.models.input_models.rekognition_config import RekognitionConfig
from app.models.input_models.transcribe_config import TranscribeConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.service_catalog import build_service_catalog

SERVICE_CONFIGS = {
    ServiceType.COMPREHEND: ComprehendConfig(),
    ServiceType.REKOGNITION: RekognitionConfig(),
    ServiceType.TRANSCRIBE: TranscribeConfig(),
    ServiceType.KENDRA: KendraConfig(),
    ServiceType.LEX: LexConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_machine_learning_api_generators_emit_typed_terraform(
    service_type, config
) -> None:
    instance = ResourceInstanceIR(
        name="ml_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


@pytest.mark.parametrize(
    "service_type",
    [
        ServiceType.COMPREHEND_MEDICAL,
        ServiceType.TEXTRACT,
        ServiceType.TRANSLATE,
        ServiceType.PERSONALIZE,
        ServiceType.FORECAST,
        ServiceType.FRAUD_DETECTOR,
        ServiceType.HEALTHLAKE,
    ],
)
def test_api_only_services_are_capabilities(service_type) -> None:
    metadata = build_service_catalog()[service_type]
    assert metadata.classification.value == "capability"
    assert not metadata.capabilities.terraform
