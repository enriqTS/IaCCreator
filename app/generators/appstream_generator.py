"""AppStream service generator — produces HCL for aws_appstream_fleet resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class AppStreamGenerator:
    """Generates Terraform files for AppStream fleets."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_appstream_fleet resource."""
        attrs: dict = {"name": "var.fleet_name"}
        if instance.config.appstream_instance_type is not None:
            attrs["instance_type"] = "var.instance_type"

        return self._r.render_resource("aws_appstream_fleet", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an AppStream fleet."""
        parts = [
            self._r.render_variable("fleet_name", "string", "Name of the AppStream fleet"),
        ]
        if instance.config.appstream_instance_type is not None:
            parts.append(self._r.render_variable(
                "instance_type", "string", "Instance type for the AppStream fleet",
                default=instance.config.appstream_instance_type,
            ))
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
