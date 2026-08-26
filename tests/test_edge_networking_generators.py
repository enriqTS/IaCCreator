"""Tests for edge networking generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.cloudfront_config import CloudFrontConfig
from app.models.input_models.load_balancer_config import LoadBalancerConfig
from app.models.input_models.route53_config import Route53Config
from app.models.input_models.target_group_config import TargetGroupConfig
from app.models.ir_models import ResourceInstanceIR

EDGE_CONFIGS = {
    ServiceType.LOAD_BALANCER: LoadBalancerConfig(),
    ServiceType.TARGET_GROUP: TargetGroupConfig(),
    ServiceType.ROUTE53: Route53Config(),
    ServiceType.CLOUDFRONT: CloudFrontConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), EDGE_CONFIGS.items())
def test_edge_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="edge_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_network_load_balancer_omits_security_groups() -> None:
    instance = ResourceInstanceIR(
        name="network_lb",
        service_type=ServiceType.LOAD_BALANCER,
        config=LoadBalancerConfig(load_balancer_type="network"),
    )
    generator = GENERATOR_REGISTRY[ServiceType.LOAD_BALANCER]
    assert "security_groups" not in generator.generate_resource_tf(instance)


def test_private_route53_zone_uses_dynamic_vpc_block() -> None:
    instance = ResourceInstanceIR(
        name="private_zone",
        service_type=ServiceType.ROUTE53,
        config=Route53Config(
            private_zone=True, vpc_id="vpc-123", vpc_region="us-east-1"
        ),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.ROUTE53].generate_resource_tf(instance)
    assert 'dynamic "vpc"' in hcl
    assert "var.private_zone ? [1] : []" in hcl
