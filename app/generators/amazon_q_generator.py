"""Amazon Q service generator — produces HCL for aws_qbusiness_application resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
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
            "identity_type": "var.identity_type",
            "tags": "var.tags",
        }
        return self._r.render_resource(
            "aws_qbusiness_application", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf dynamically from VARIABLE_SCHEMAS."""
        schema = VARIABLE_SCHEMAS[ServiceType.AMAZON_Q]
        parts = []
        for entry in schema:
            tf_type = "map(string)" if entry.type == "map" else entry.type
            parts.append(
                self._r.render_variable(
                    entry.name, tf_type, entry.description, entry.default
                )
            )
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
