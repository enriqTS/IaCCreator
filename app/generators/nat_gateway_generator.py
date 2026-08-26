"""Terraform generator for NAT gateways."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.nat_gateway_config import NatGatewayConfig
from app.models.ir_models import ResourceInstanceIR


class NatGatewayGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, NatGatewayConfig)
        attrs = {
            "subnet_id": Expr("var.subnet_id"),
            "connectivity_type": Expr("var.connectivity_type"),
        }
        if config.connectivity_type == "public":
            attrs["allocation_id"] = Expr("var.allocation_id")
        return self._r.render_resource("aws_nat_gateway", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, NatGatewayConfig)
        parts = [
            self._r.render_variable("subnet_id", "string", "Subnet ID"),
            self._r.render_variable("connectivity_type", "string", "Connectivity type"),
        ]
        if config.connectivity_type == "public":
            parts.append(
                self._r.render_variable(
                    "allocation_id", "string", "Elastic IP allocation ID"
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return self._r.render_output(
            "nat_gateway_id", f"aws_nat_gateway.{instance.name}.id", "NAT gateway ID"
        )
