"""Tests for foundational security service generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.acm_config import AcmConfig
from app.models.input_models.cognito_config import CognitoConfig
from app.models.input_models.kms_config import KmsConfig
from app.models.input_models.secrets_manager_config import SecretsManagerConfig
from app.models.input_models.waf_config import WafConfig
from app.models.ir_models import ResourceInstanceIR

SECURITY_CONFIGS = {
    ServiceType.KMS: KmsConfig(),
    ServiceType.SECRETS_MANAGER: SecretsManagerConfig(),
    ServiceType.COGNITO: CognitoConfig(),
    ServiceType.CERTIFICATE_MANAGER: AcmConfig(),
    ServiceType.WAF: WafConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SECURITY_CONFIGS.items())
def test_security_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="security_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_kms_alias_references_generated_key() -> None:
    instance = ResourceInstanceIR(
        name="app_key", service_type=ServiceType.KMS, config=KmsConfig(alias="app")
    )
    hcl = GENERATOR_REGISTRY[ServiceType.KMS].generate_resource_tf(instance)
    assert 'resource "aws_kms_alias"' in hcl
    assert "aws_kms_key.app_key.key_id" in hcl


def test_cognito_client_references_user_pool() -> None:
    instance = ResourceInstanceIR(
        name="users", service_type=ServiceType.COGNITO, config=CognitoConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.COGNITO].generate_resource_tf(instance)
    assert "aws_cognito_user_pool.users.id" in hcl


def test_waf_default_action_is_rendered_as_block() -> None:
    instance = ResourceInstanceIR(
        name="edge_acl",
        service_type=ServiceType.WAF,
        config=WafConfig(default_action="block"),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.WAF].generate_resource_tf(instance)
    assert "default_action" in hcl
    assert "block" in hcl
