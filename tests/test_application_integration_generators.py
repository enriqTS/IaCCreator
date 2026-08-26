"""Tests for foundational application integration generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.appsync_config import AppSyncConfig
from app.models.input_models.mq_config import MqConfig
from app.models.input_models.mwaa_config import MwaaConfig
from app.models.input_models.step_functions_config import StepFunctionsConfig
from app.models.ir_models import ResourceInstanceIR

INTEGRATION_CONFIGS = {
    ServiceType.STEP_FUNCTIONS: StepFunctionsConfig(
        role_arn="arn:aws:iam::123456789012:role/sfn"
    ),
    ServiceType.APPSYNC: AppSyncConfig(),
    ServiceType.MQ: MqConfig(subnet_ids=["subnet-123"], password="not-a-real-password"),
    ServiceType.MWAA: MwaaConfig(
        execution_role_arn="arn:aws:iam::123456789012:role/mwaa",
        source_bucket_arn="arn:aws:s3:::workflows",
        subnet_ids=["subnet-1", "subnet-2"],
        security_group_ids=["sg-123"],
    ),
}


@pytest.mark.parametrize(("service_type", "config"), INTEGRATION_CONFIGS.items())
def test_integration_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="integration_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_appsync_api_key_references_graphql_api() -> None:
    instance = ResourceInstanceIR(
        name="api", service_type=ServiceType.APPSYNC, config=AppSyncConfig()
    )
    hcl = GENERATOR_REGISTRY[ServiceType.APPSYNC].generate_resource_tf(instance)
    assert 'resource "aws_appsync_api_key"' in hcl
    assert "aws_appsync_graphql_api.api.id" in hcl


def test_mq_user_password_uses_variable_reference() -> None:
    instance = ResourceInstanceIR(
        name="broker",
        service_type=ServiceType.MQ,
        config=MqConfig(subnet_ids=["subnet-123"], password="not-a-real-password"),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.MQ].generate_resource_tf(instance)
    assert "password = var.password" in hcl
    assert "not-a-real-password" not in hcl


def test_mwaa_network_configuration_uses_module_inputs() -> None:
    config = INTEGRATION_CONFIGS[ServiceType.MWAA]
    instance = ResourceInstanceIR(
        name="airflow", service_type=ServiceType.MWAA, config=config
    )
    hcl = GENERATOR_REGISTRY[ServiceType.MWAA].generate_resource_tf(instance)
    assert "subnet_ids = var.subnet_ids" in hcl
    assert "security_group_ids = var.security_group_ids" in hcl
