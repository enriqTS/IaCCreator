"""Terraform generator for AWS X-Ray groups."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.xray_filters import (
    lambda_group_filter_expression,
    lambda_group_preconditions,
)
from app.models.input_models.xray_config import XRayConfig
from app.models.ir_models import ResourceInstanceIR


class XRayGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, XRayConfig)
        attrs = {
            "group_name": Expr("var.group_name"),
            "filter_expression": Expr("var.filter_expression"),
            "insights_configuration": [
                {
                    "insights_enabled": Expr("var.insights_enabled"),
                    "notifications_enabled": Expr("var.notifications_enabled"),
                }
            ],
        }
        if config._managed_lambda_tracing:
            attrs["filter_expression"] = lambda_group_filter_expression()
            attrs["lifecycle"] = {"precondition": lambda_group_preconditions()}
        return self._r.render_resource(
            "aws_xray_group",
            instance.name,
            attrs,
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, XRayConfig)
        fields = [
            ("group_name", "string", "X-Ray group name"),
            ("filter_expression", "string", "Trace filter expression"),
            ("insights_enabled", "bool", "Enable X-Ray Insights"),
            ("notifications_enabled", "bool", "Enable Insights notifications"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_xray_group.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("group_arn", f"{ref}.arn", "X-Ray group ARN"),
                self._r.render_output(
                    "group_name", f"{ref}.group_name", "X-Ray group name"
                ),
            ]
        )
