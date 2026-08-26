"""Terraform generator for Application Auto Scaling targets."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.application_auto_scaling_config import (
    ApplicationAutoScalingConfig,
)
from app.models.ir_models import ResourceInstanceIR


class ApplicationAutoScalingGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, ApplicationAutoScalingConfig)
        target = self._r.render_resource(
            "aws_appautoscaling_target",
            instance.name,
            {
                "service_namespace": Expr("var.service_namespace"),
                "resource_id": Expr("var.resource_id"),
                "scalable_dimension": Expr("var.scalable_dimension"),
                "min_capacity": Expr("var.min_capacity"),
                "max_capacity": Expr("var.max_capacity"),
            },
        )
        if not config.create_target_tracking_policy:
            return target
        policy = self._r.render_resource(
            "aws_appautoscaling_policy",
            instance.name,
            {
                "name": f"{instance.name}-target-tracking",
                "policy_type": "TargetTrackingScaling",
                "service_namespace": Expr(
                    f"aws_appautoscaling_target.{instance.name}.service_namespace"
                ),
                "resource_id": Expr(
                    f"aws_appautoscaling_target.{instance.name}.resource_id"
                ),
                "scalable_dimension": Expr(
                    f"aws_appautoscaling_target.{instance.name}.scalable_dimension"
                ),
                "target_tracking_scaling_policy_configuration": [
                    {
                        "target_value": Expr("var.target_value"),
                        "scale_in_cooldown": Expr("var.scale_in_cooldown"),
                        "scale_out_cooldown": Expr("var.scale_out_cooldown"),
                        "predefined_metric_specification": [
                            {
                                "predefined_metric_type": Expr(
                                    "var.predefined_metric_type"
                                ),
                            }
                        ],
                    }
                ],
            },
        )
        return target + policy

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ApplicationAutoScalingConfig)
        fields = [
            ("service_namespace", "string", "AWS service namespace"),
            ("resource_id", "string", "Scalable resource identifier"),
            ("scalable_dimension", "string", "Scalable property dimension"),
            ("min_capacity", "number", "Minimum capacity"),
            ("max_capacity", "number", "Maximum capacity"),
            (
                "create_target_tracking_policy",
                "bool",
                "Create a target tracking policy",
            ),
            ("predefined_metric_type", "string", "Predefined target tracking metric"),
            ("target_value", "number", "Metric target value"),
            ("scale_in_cooldown", "number", "Scale-in cooldown"),
            ("scale_out_cooldown", "number", "Scale-out cooldown"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, ApplicationAutoScalingConfig)
        ref = f"aws_appautoscaling_target.{instance.name}"
        parts = [
            self._r.render_output(
                "scalable_target_id", f"{ref}.id", "Scalable target ID"
            )
        ]
        if config.create_target_tracking_policy:
            parts.append(
                self._r.render_output(
                    "scaling_policy_arn",
                    f"aws_appautoscaling_policy.{instance.name}.arn",
                    "Scaling policy ARN",
                )
            )
        return "\n".join(parts)
