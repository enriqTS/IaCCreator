"""Tests for EC2 and Application Auto Scaling generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.application_auto_scaling_config import (
    ApplicationAutoScalingConfig,
)
from app.models.input_models.ec2_auto_scaling_config import Ec2AutoScalingConfig
from app.models.ir_models import ResourceInstanceIR

SCALING_CONFIGS = {
    ServiceType.EC2_AUTO_SCALING: Ec2AutoScalingConfig(),
    ServiceType.APPLICATION_AUTO_SCALING: ApplicationAutoScalingConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SCALING_CONFIGS.items())
def test_auto_scaling_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="scaler", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_ec2_auto_scaling_references_launch_template_inputs() -> None:
    instance = ResourceInstanceIR(
        name="workers",
        service_type=ServiceType.EC2_AUTO_SCALING,
        config=Ec2AutoScalingConfig(
            launch_template_id="lt-123", subnet_ids=["subnet-123"]
        ),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.EC2_AUTO_SCALING].generate_resource_tf(
        instance
    )
    assert "id = var.launch_template_id" in hcl
    assert "vpc_zone_identifier = var.subnet_ids" in hcl
    assert "lt-123" not in hcl


def test_application_auto_scaling_policy_references_target() -> None:
    instance = ResourceInstanceIR(
        name="service_capacity",
        service_type=ServiceType.APPLICATION_AUTO_SCALING,
        config=ApplicationAutoScalingConfig(resource_id="service/cluster/api"),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.APPLICATION_AUTO_SCALING].generate_resource_tf(
        instance
    )
    assert 'resource "aws_appautoscaling_policy"' in hcl
    assert "aws_appautoscaling_target.service_capacity.resource_id" in hcl
