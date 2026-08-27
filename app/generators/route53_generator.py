"""Terraform generator for Route 53 hosted zones."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.route53_config import Route53Config
from app.models.ir_models import ResourceInstanceIR


class Route53Generator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, Route53Config)
        attrs = {"name": Expr("var.zone_name")}
        if config.comment is not None:
            attrs["comment"] = Expr("var.comment")
        attrs['dynamic "vpc"'] = {
            "for_each": Expr("var.private_zone ? [1] : []"),
            "content": {
                "vpc_id": Expr("var.vpc_id"),
                "vpc_region": Expr('var.vpc_region == "" ? null : var.vpc_region'),
            },
        }
        return self._r.render_resource("aws_route53_zone", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, Route53Config)
        parts = [self._r.render_variable("zone_name", "string", "DNS zone name")]
        if config.comment is not None:
            parts.append(
                self._r.render_variable("comment", "string", "Hosted zone comment")
            )
        parts.extend(
            [
                self._r.render_variable(
                    "private_zone", "bool", "Create a private hosted zone"
                ),
                self._r.render_variable("vpc_id", "string", "VPC ID", default=""),
                self._r.render_variable(
                    "vpc_region", "string", "VPC region", default=""
                ),
            ]
        )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "zone_id",
                    f"aws_route53_zone.{instance.name}.zone_id",
                    "Hosted zone ID",
                ),
                self._r.render_output(
                    "name_servers",
                    f"aws_route53_zone.{instance.name}.name_servers",
                    "Hosted zone name servers",
                ),
            ]
        )
