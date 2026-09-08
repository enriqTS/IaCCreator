"""Terraform launch templates with reusable security-group placement."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.ec2_launch_template_config import Ec2LaunchTemplateConfig
from app.models.ir_models import ResourceInstanceIR


class Ec2LaunchTemplateGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, Ec2LaunchTemplateConfig)
        attrs = {
            "name_prefix": f"{instance.name}-",
            "image_id": Expr("var.image_id"),
            "instance_type": Expr("var.instance_type"),
            "vpc_security_group_ids": Expr("var.security_group_ids"),
            "metadata_options": {"http_tokens": "required"},
        }
        for name in ("key_name", "user_data"):
            if getattr(config, name) is not None:
                attrs[name] = Expr(f"var.{name}")
        if config.iam_instance_profile_name is not None:
            attrs["iam_instance_profile"] = {
                "name": Expr("var.iam_instance_profile_name")
            }
        return self._r.render_resource("aws_launch_template", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, Ec2LaunchTemplateConfig)
        return "\n".join(
            self._r.render_variable(
                field.name,
                "list(string)" if field.type == "list" else field.type,
                field.description,
            )
            for field in config.get_variable_schema()
            if getattr(config, field.name) is not None
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_launch_template.{instance.name}"
        return "\n".join(
            self._r.render_output(name, f"{ref}.{attribute}", description)
            for name, attribute, description in (
                ("launch_template_id", "id", "Launch template ID"),
                ("launch_template_arn", "arn", "Launch template ARN"),
                (
                    "latest_version",
                    "latest_version",
                    "Latest numeric launch template version",
                ),
            )
        )
