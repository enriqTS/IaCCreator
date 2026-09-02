"""Terraform generator for EC2 Auto Scaling groups."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.ec2_auto_scaling_config import Ec2AutoScalingConfig
from app.models.ir_models import ResourceInstanceIR


class Ec2AutoScalingGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, Ec2AutoScalingConfig)
        return self._r.render_resource(
            "aws_autoscaling_group",
            instance.name,
            {
                "name": instance.name,
                "vpc_zone_identifier": Expr("var.subnet_ids"),
                "target_group_arns": Expr("var.target_group_arns"),
                "min_size": Expr("var.min_size"),
                "max_size": Expr("var.max_size"),
                "desired_capacity": Expr("var.desired_capacity"),
                "health_check_type": Expr("var.health_check_type"),
                "health_check_grace_period": Expr("var.health_check_grace_period"),
                "termination_policies": Expr("var.termination_policies"),
                "launch_template": [
                    {
                        "id": Expr("var.launch_template_id"),
                        "version": Expr("var.launch_template_version"),
                    }
                ],
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, Ec2AutoScalingConfig)
        fields = [
            ("launch_template_id", "string", "EC2 launch template ID"),
            ("launch_template_version", "string", "Launch template version"),
            ("subnet_ids", "list(string)", "Auto Scaling group subnet IDs"),
            ("target_group_arns", "list(string)", "Attached target group ARNs"),
            ("min_size", "number", "Minimum instance count"),
            ("max_size", "number", "Maximum instance count"),
            ("desired_capacity", "number", "Desired instance count"),
            ("health_check_type", "string", "Health check source"),
            ("health_check_grace_period", "number", "Health check grace period"),
            ("termination_policies", "list(string)", "Instance termination policies"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_autoscaling_group.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "autoscaling_group_id", f"{ref}.id", "Auto Scaling group ID"
                ),
                self._r.render_output(
                    "autoscaling_group_arn", f"{ref}.arn", "Auto Scaling group ARN"
                ),
                self._r.render_output(
                    "autoscaling_group_name", f"{ref}.name", "Auto Scaling group name"
                ),
            ]
        )
