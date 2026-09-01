"""Gateway-to-route-table connection coverage."""

import pytest
from pydantic import ValidationError

from app.models.connection_configs.configs import GatewayRouteConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


@pytest.mark.parametrize(
    "source,argument,output",
    [
        (ServiceType.INTERNET_GATEWAY, "gateway_id", "internet_gateway_id"),
        (ServiceType.NAT_GATEWAY, "nat_gateway_id", "nat_gateway_id"),
        (ServiceType.TRANSIT_GATEWAY, "transit_gateway_id", "transit_gateway_id"),
    ],
)
def test_gateway_route_uses_the_gateway_specific_argument(source, argument, output):
    spec = resolve_spec(source, ServiceType.ROUTE_TABLE, "routes", {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["connections"][0]["connection_config"] = {
        "destination_cidr_block": "10.20.0.0/16"
    }

    tree = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )
    route = tree[
        "connection-check/modules/networking/route-table/target-resource/"
        "route_source_resource.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert 'destination_cidr_block = "10.20.0.0/16"' in route
    assert f"{argument} = var.source_resource_gateway_id" in route
    assert (
        f"source_resource_gateway_id = module.source-resource.{output}" in environment
    )


@pytest.mark.parametrize("cidr", ["10.0.0.1/24", "10.0.0.0/33", "not-a-cidr"])
def test_gateway_route_rejects_invalid_network_cidrs(cidr):
    with pytest.raises(ValidationError, match="destination_cidr_block"):
        GatewayRouteConfig(destination_cidr_block=cidr)


def test_network_firewall_has_vpc_membership():
    spec = resolve_spec(ServiceType.VPC, ServiceType.NETWORK_FIREWALL, "contains", {})
    assert spec is not None
