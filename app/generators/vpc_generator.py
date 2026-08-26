"""Terraform generator for VPCs."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.vpc_config import VpcConfig
from app.models.ir_models import ResourceInstanceIR


class VpcGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, VpcConfig)
        return self._r.render_resource(
            "aws_vpc",
            instance.name,
            {
                "cidr_block": Expr("var.cidr_block"),
                "instance_tenancy": Expr("var.instance_tenancy"),
                "enable_dns_support": Expr("var.enable_dns_support"),
                "enable_dns_hostnames": Expr("var.enable_dns_hostnames"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_variable("cidr_block", "string", "IPv4 CIDR block"),
                self._r.render_variable(
                    "instance_tenancy", "string", "Instance tenancy"
                ),
                self._r.render_variable(
                    "enable_dns_support", "bool", "Enable DNS resolution"
                ),
                self._r.render_variable(
                    "enable_dns_hostnames", "bool", "Enable DNS hostnames"
                ),
            ]
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "vpc_id", f"aws_vpc.{instance.name}.id", "VPC ID"
                ),
                self._r.render_output(
                    "vpc_arn", f"aws_vpc.{instance.name}.arn", "VPC ARN"
                ),
                self._r.render_output(
                    "default_route_table_id",
                    f"aws_vpc.{instance.name}.default_route_table_id",
                    "Default route table ID",
                ),
            ]
        )
