"""Terraform generator for AWS WAFv2 web ACLs."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.waf_config import WafConfig
from app.models.ir_models import ResourceInstanceIR


class WafGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, WafConfig)
        attrs = {
            "name": instance.name,
            "scope": Expr("var.scope"),
            "default_action": [{config.default_action: {}}],
            "visibility_config": [
                {
                    "cloudwatch_metrics_enabled": Expr(
                        "var.cloudwatch_metrics_enabled"
                    ),
                    "metric_name": instance.name,
                    "sampled_requests_enabled": Expr("var.sampled_requests_enabled"),
                }
            ],
        }
        if config.description is not None:
            attrs["description"] = Expr("var.description")
        return self._r.render_resource("aws_wafv2_web_acl", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, WafConfig)
        parts = [
            self._r.render_variable("scope", "string", "Web ACL scope"),
            self._r.render_variable("default_action", "string", "Default action"),
            self._r.render_variable(
                "cloudwatch_metrics_enabled", "bool", "Publish CloudWatch metrics"
            ),
            self._r.render_variable(
                "sampled_requests_enabled", "bool", "Store sampled requests"
            ),
        ]
        if config.description is not None:
            parts.append(
                self._r.render_variable("description", "string", "Web ACL description")
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_wafv2_web_acl.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("web_acl_id", f"{ref}.id", "Web ACL ID"),
                self._r.render_output("web_acl_arn", f"{ref}.arn", "Web ACL ARN"),
            ]
        )
