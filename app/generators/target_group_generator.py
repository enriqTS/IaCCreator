"""Terraform generator for load balancer target groups."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.target_group_config import TargetGroupConfig
from app.models.ir_models import ResourceInstanceIR


class TargetGroupGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, TargetGroupConfig)
        attrs = {
            "name": Expr("var.target_group_name"),
            "port": Expr("var.port"),
            "protocol": Expr("var.protocol"),
            "target_type": Expr("var.target_type"),
            "vpc_id": Expr("var.vpc_id"),
        }
        if config.protocol in {"HTTP", "HTTPS"}:
            attrs["health_check"] = [{"path": Expr("var.health_check_path")}]
        return self._r.render_resource("aws_lb_target_group", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, TargetGroupConfig)
        parts = [
            self._r.render_variable("target_group_name", "string", "Target group name"),
            self._r.render_variable("vpc_id", "string", "VPC ID"),
            self._r.render_variable("port", "number", "Traffic port"),
            self._r.render_variable("protocol", "string", "Traffic protocol"),
            self._r.render_variable("target_type", "string", "Target type"),
        ]
        if config.protocol in {"HTTP", "HTTPS"}:
            parts.append(
                self._r.render_variable(
                    "health_check_path", "string", "HTTP health check path"
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return self._r.render_output(
            "target_group_arn",
            f"aws_lb_target_group.{instance.name}.arn",
            "Target group ARN",
        )
