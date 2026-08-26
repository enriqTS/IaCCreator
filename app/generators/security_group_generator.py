"""Terraform generator for security groups."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.security_group_config import SecurityGroupConfig
from app.models.ir_models import ResourceInstanceIR


class SecurityGroupGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, SecurityGroupConfig)
        attrs = {
            "name": instance.name,
            "description": Expr("var.description"),
            "vpc_id": Expr("var.vpc_id"),
            "ingress": [
                {
                    "description": "Managed ingress",
                    "from_port": Expr("var.ingress_from_port"),
                    "to_port": Expr("var.ingress_to_port"),
                    "protocol": Expr("var.ingress_protocol"),
                    "cidr_blocks": [Expr("var.ingress_cidr")],
                }
            ],
        }
        if config.allow_all_egress:
            attrs["egress"] = [
                {
                    "from_port": 0,
                    "to_port": 0,
                    "protocol": "-1",
                    "cidr_blocks": ["0.0.0.0/0"],
                }
            ]
        return self._r.render_resource("aws_security_group", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_variable("vpc_id", "string", "VPC ID"),
                self._r.render_variable(
                    "description", "string", "Security group description"
                ),
                self._r.render_variable(
                    "ingress_protocol", "string", "Ingress protocol"
                ),
                self._r.render_variable(
                    "ingress_from_port", "number", "First ingress port"
                ),
                self._r.render_variable(
                    "ingress_to_port", "number", "Last ingress port"
                ),
                self._r.render_variable("ingress_cidr", "string", "Allowed IPv4 CIDR"),
            ]
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "security_group_id",
                    f"aws_security_group.{instance.name}.id",
                    "Security group ID",
                ),
                self._r.render_output(
                    "security_group_arn",
                    f"aws_security_group.{instance.name}.arn",
                    "Security group ARN",
                ),
            ]
        )
