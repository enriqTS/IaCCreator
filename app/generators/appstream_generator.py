"""AppStream service generator — produces HCL for aws_appstream_fleet resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.appstream_config import AppStreamConfig
from app.models.ir_models import ResourceInstanceIR


class AppStreamGenerator:
    """Generates Terraform files for AppStream fleets."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_appstream_fleet resource."""
        config = get_typed_config(instance, AppStreamConfig)

        attrs: dict = {"name": "var.fleet_name"}
        if config.instance_type is not None:
            attrs["instance_type"] = "var.instance_type"

        return self._r.render_resource("aws_appstream_fleet", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an AppStream fleet."""
        config = get_typed_config(instance, AppStreamConfig)

        parts = [
            self._r.render_variable(
                "fleet_name", "string", "Name of the AppStream fleet"
            ),
        ]
        if config.instance_type is not None:
            parts.append(
                self._r.render_variable(
                    "instance_type",
                    "string",
                    "Instance type for the AppStream fleet",
                    default=config.instance_type,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an AppStream fleet."""
        parts = [
            self._r.render_output(
                "fleet_arn",
                f"aws_appstream_fleet.{instance.name}.arn",
                "ARN of the AppStream fleet",
            ),
            self._r.render_output(
                "fleet_name",
                f"aws_appstream_fleet.{instance.name}.name",
                "Name of the AppStream fleet",
            ),
        ]
        return "\n".join(parts)
