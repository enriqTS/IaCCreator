"""CodeDeploy service generator — produces HCL for aws_codedeploy_app resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.codedeploy_config import CodeDeployConfig
from app.models.ir_models import ResourceInstanceIR


class CodeDeployGenerator:
    """Generates Terraform files for CodeDeploy applications."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codedeploy_app resource."""
        config = get_typed_config(instance, CodeDeployConfig)

        attrs: dict = {"name": "var.app_name"}
        if config.compute_platform is not None:
            attrs["compute_platform"] = "var.compute_platform"

        return self._r.render_resource("aws_codedeploy_app", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CodeDeploy application."""
        config = get_typed_config(instance, CodeDeployConfig)

        parts = [
            self._r.render_variable(
                "app_name", "string", "Name of the CodeDeploy application"
            ),
        ]
        if config.compute_platform is not None:
            parts.append(
                self._r.render_variable(
                    "compute_platform",
                    "string",
                    "Compute platform for the CodeDeploy application",
                    default=config.compute_platform,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a CodeDeploy application."""
        parts = [
            self._r.render_output(
                "app_id",
                f"aws_codedeploy_app.{instance.name}.id",
                "ID of the CodeDeploy application",
            ),
            self._r.render_output(
                "app_name",
                f"aws_codedeploy_app.{instance.name}.name",
                "Name of the CodeDeploy application",
            ),
        ]
        return "\n".join(parts)
