"""Pinpoint service generator — produces HCL for aws_pinpoint_app resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.pinpoint_config import PinpointConfig
from app.models.ir_models import ResourceInstanceIR


class PinpointGenerator:
    """Generates Terraform files for Pinpoint applications."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_pinpoint_app resource."""
        get_typed_config(instance, PinpointConfig)

        attrs: dict = {"name": "var.app_name"}

        return self._r.render_resource("aws_pinpoint_app", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Pinpoint application."""
        get_typed_config(instance, PinpointConfig)

        parts = [
            self._r.render_variable(
                "app_name", "string", "Name of the Pinpoint application"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Pinpoint application."""
        parts = [
            self._r.render_output(
                "application_id",
                f"aws_pinpoint_app.{instance.name}.application_id",
                "Application ID of the Pinpoint application",
            ),
            self._r.render_output(
                "app_arn",
                f"aws_pinpoint_app.{instance.name}.arn",
                "ARN of the Pinpoint application",
            ),
        ]
        return "\n".join(parts)
