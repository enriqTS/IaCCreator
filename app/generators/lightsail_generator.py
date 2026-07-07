"""Lightsail service generator — produces HCL for aws_lightsail_instance resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.lightsail_config import LightsailConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> LightsailConfig:
    """Resolve typed LightsailConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, LightsailConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class LightsailGenerator:
    """Generates Terraform files for Lightsail instances."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_lightsail_instance resource."""
        _resolve_config(instance)

        attrs: dict = {
            "name": "var.instance_name",
            "blueprint_id": "var.blueprint_id",
            "bundle_id": "var.bundle_id",
            "availability_zone": "var.availability_zone",
        }

        return self._r.render_resource("aws_lightsail_instance", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Lightsail instance."""
        _resolve_config(instance)

        parts = [
            self._r.render_variable(
                "instance_name", "string", "Name of the Lightsail instance"
            ),
            self._r.render_variable(
                "blueprint_id", "string", "Blueprint ID for the Lightsail instance"
            ),
            self._r.render_variable(
                "bundle_id", "string", "Bundle ID for the Lightsail instance"
            ),
            self._r.render_variable(
                "availability_zone",
                "string",
                "Availability zone for the Lightsail instance",
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Lightsail instance."""
        parts = [
            self._r.render_output(
                "instance_arn",
                f"aws_lightsail_instance.{instance.name}.arn",
                "ARN of the Lightsail instance",
            ),
            self._r.render_output(
                "instance_name",
                f"aws_lightsail_instance.{instance.name}.name",
                "Name of the Lightsail instance",
            ),
        ]
        return "\n".join(parts)
