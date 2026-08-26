"""Terraform generator for elastic load balancers."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.load_balancer_config import LoadBalancerConfig
from app.models.ir_models import ResourceInstanceIR


class LoadBalancerGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, LoadBalancerConfig)
        attrs = {
            "name": Expr("var.load_balancer_name"),
            "load_balancer_type": Expr("var.load_balancer_type"),
            "internal": Expr("var.internal"),
            "subnets": Expr('compact(split(",", var.subnet_ids))'),
            "enable_deletion_protection": Expr("var.enable_deletion_protection"),
        }
        if config.load_balancer_type == "application":
            attrs["security_groups"] = Expr(
                'compact(split(",", var.security_group_ids))'
            )
        return self._r.render_resource("aws_lb", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, LoadBalancerConfig)
        parts = [
            self._r.render_variable(
                "load_balancer_name", "string", "Load balancer name"
            ),
            self._r.render_variable(
                "load_balancer_type", "string", "Load balancer type"
            ),
            self._r.render_variable("internal", "bool", "Use an internal scheme"),
            self._r.render_variable(
                "subnet_ids", "string", "Comma-separated subnet IDs"
            ),
            self._r.render_variable(
                "enable_deletion_protection", "bool", "Enable deletion protection"
            ),
        ]
        if config.load_balancer_type == "application":
            parts.append(
                self._r.render_variable(
                    "security_group_ids", "string", "Comma-separated security group IDs"
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "load_balancer_arn",
                    f"aws_lb.{instance.name}.arn",
                    "Load balancer ARN",
                ),
                self._r.render_output(
                    "dns_name",
                    f"aws_lb.{instance.name}.dns_name",
                    "Load balancer DNS name",
                ),
                self._r.render_output(
                    "zone_id",
                    f"aws_lb.{instance.name}.zone_id",
                    "Canonical hosted zone ID",
                ),
            ]
        )
