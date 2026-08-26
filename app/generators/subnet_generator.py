"""Terraform generator for subnets."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.subnet_config import SubnetConfig
from app.models.ir_models import ResourceInstanceIR


class SubnetGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, SubnetConfig)
        attrs = {
            "vpc_id": Expr("var.vpc_id"),
            "cidr_block": Expr("var.cidr_block"),
            "map_public_ip_on_launch": Expr("var.map_public_ip_on_launch"),
        }
        if config.availability_zone is not None:
            attrs["availability_zone"] = Expr("var.availability_zone")
        return self._r.render_resource("aws_subnet", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, SubnetConfig)
        parts = [
            self._r.render_variable("vpc_id", "string", "VPC ID"),
            self._r.render_variable("cidr_block", "string", "IPv4 CIDR block"),
            self._r.render_variable(
                "map_public_ip_on_launch", "bool", "Assign public IPv4 addresses"
            ),
        ]
        if config.availability_zone is not None:
            parts.append(
                self._r.render_variable(
                    "availability_zone", "string", "Availability Zone"
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "subnet_id", f"aws_subnet.{instance.name}.id", "Subnet ID"
                ),
                self._r.render_output(
                    "subnet_arn", f"aws_subnet.{instance.name}.arn", "Subnet ARN"
                ),
            ]
        )
