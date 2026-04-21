"""GameLift service generator — produces HCL for aws_gamelift_fleet resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class GameLiftGenerator:
    """Generates Terraform files for GameLift fleets."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_gamelift_fleet resource."""
        attrs: dict = {"name": "var.fleet_name"}
        if instance.config.gamelift_ec2_instance_type is not None:
            attrs["ec2_instance_type"] = "var.ec2_instance_type"

        return self._r.render_resource("aws_gamelift_fleet", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a GameLift fleet."""
        parts = [
            self._r.render_variable("fleet_name", "string", "Name of the GameLift fleet"),
        ]
        if instance.config.gamelift_ec2_instance_type is not None:
            parts.append(self._r.render_variable(
                "ec2_instance_type", "string", "EC2 instance type for the GameLift fleet",
                default=instance.config.gamelift_ec2_instance_type,
            ))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a GameLift fleet."""
        parts = [
            self._r.render_output(
                "fleet_arn",
                f"aws_gamelift_fleet.{instance.name}.arn",
                "ARN of the GameLift fleet",
            ),
            self._r.render_output(
                "fleet_id",
                f"aws_gamelift_fleet.{instance.name}.id",
                "ID of the GameLift fleet",
            ),
        ]
        return "\n".join(parts)
