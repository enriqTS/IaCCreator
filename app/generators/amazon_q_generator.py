"""Amazon Q service generator — produces HCL for aws_qbusiness_application resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class AmazonQGenerator:
    """Generates Terraform files for Amazon Q Business applications."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_qbusiness_application resource."""
        attrs: dict = {
            "display_name": "var.application_name",
            "description": "var.description",
            "role_arn": "var.role_arn",
        }
        return self._r.render_resource("aws_qbusiness_application", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an Amazon Q application."""
        parts = [
            self._r.render_variable("application_name", "string", "Name of the Amazon Q application"),
            self._r.render_variable("description", "string", "Description of the Amazon Q application"),
            self._r.render_variable("role_arn", "string", "IAM role ARN for the Amazon Q application"),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an Amazon Q application."""
        parts = [
            self._r.render_output(
                "application_id",
                f"aws_qbusiness_application.{instance.name}.id",
                "ID of the Amazon Q application",
            ),
            self._r.render_output(
                "application_arn",
                f"aws_qbusiness_application.{instance.name}.arn",
                "ARN of the Amazon Q application",
            ),
        ]
        return "\n".join(parts)
