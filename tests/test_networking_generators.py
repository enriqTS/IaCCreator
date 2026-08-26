"""Tests for foundational networking models and generators."""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.internet_gateway_config import InternetGatewayConfig
from app.models.input_models.nat_gateway_config import NatGatewayConfig
from app.models.input_models.route_table_config import RouteTableConfig
from app.models.input_models.security_group_config import SecurityGroupConfig
from app.models.input_models.subnet_config import SubnetConfig
from app.models.input_models.vpc_config import VpcConfig
from app.models.ir_models import ResourceInstanceIR

NETWORKING_CONFIGS = {
    ServiceType.VPC: VpcConfig(),
    ServiceType.SUBNET: SubnetConfig(vpc_id="vpc-123"),
    ServiceType.SECURITY_GROUP: SecurityGroupConfig(vpc_id="vpc-123"),
    ServiceType.ROUTE_TABLE: RouteTableConfig(vpc_id="vpc-123"),
    ServiceType.INTERNET_GATEWAY: InternetGatewayConfig(vpc_id="vpc-123"),
    ServiceType.NAT_GATEWAY: NatGatewayConfig(
        subnet_id="subnet-123", allocation_id="eipalloc-123"
    ),
}


@pytest.mark.parametrize(("service_type", "config"), NETWORKING_CONFIGS.items())
def test_networking_generators_emit_resources_variables_and_outputs(
    service_type, config
) -> None:
    instance = ResourceInstanceIR(
        name="network_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    resource = generator.generate_resource_tf(instance)
    assert 'resource "aws_' in resource
    assert "var." in resource
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)


def test_networking_services_have_typed_models_and_schemas() -> None:
    models = get_service_config_models()
    for service_type in NETWORKING_CONFIGS:
        assert service_type in models
        assert models[service_type].has_terraform_schema()


def test_route_table_renders_configurable_route() -> None:
    generator = GENERATOR_REGISTRY[ServiceType.ROUTE_TABLE]
    instance = ResourceInstanceIR(
        name="public",
        service_type=ServiceType.ROUTE_TABLE,
        config=RouteTableConfig(vpc_id="vpc-123", gateway_id="igw-123"),
    )
    hcl = generator.generate_resource_tf(instance)
    assert "route {" in hcl
    assert "var.destination_cidr_block" in hcl
    assert "var.gateway_id" in hcl


def test_private_nat_gateway_omits_allocation_id() -> None:
    config = NatGatewayConfig(subnet_id="subnet-123", connectivity_type="private")
    instance = ResourceInstanceIR(
        name="private_nat", service_type=ServiceType.NAT_GATEWAY, config=config
    )
    generator = GENERATOR_REGISTRY[ServiceType.NAT_GATEWAY]
    assert "allocation_id" not in generator.generate_resource_tf(instance)
    assert 'variable "allocation_id"' not in generator.generate_variables_tf(instance)
