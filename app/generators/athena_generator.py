"""Athena service generator — produces HCL for aws_athena_workgroup resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class AthenaGenerator:
    """Generates Terraform files for Athena workgroups."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_athena_workgroup resource."""
        attrs: dict = {"name": "var.workgroup_name"}

        return self._r.render_resource("aws_athena_workgroup", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an Athena workgroup."""
        parts = [
            self._r.render_variable("workgroup_name", "string", "Name of the Athena workgroup"),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an Athena workgroup."""
        parts = [
            self._r.render_output(
                "workgroup_arn",
                f"aws_athena_workgroup.{instance.name}.arn",
                "ARN of the Athena workgroup",
            ),
            self._r.render_output(
                "workgroup_name",
                f"aws_athena_workgroup.{instance.name}.name",
                "Name of the Athena workgroup",
            ),
        ]
        return "\n".join(parts)
