"""Bedrock Guardrail service generator — produces HCL for aws_bedrock_guardrail resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class BedrockGuardrailGenerator:
    """Generates Terraform files for Bedrock Guardrail resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_bedrock_guardrail resource."""
        attrs: dict = {
            "name": "var.guardrail_name",
            "description": "var.description",
            "blocked_input_messaging": "var.blocked_input_messaging",
            "blocked_outputs_messaging": "var.blocked_outputs_messaging",
        }
        return self._r.render_resource("aws_bedrock_guardrail", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Bedrock Guardrail."""
        parts = [
            self._r.render_variable("guardrail_name", "string", "Name of the Bedrock Guardrail"),
            self._r.render_variable("description", "string", "Description of the guardrail"),
            self._r.render_variable("blocked_input_messaging", "string", "Message to return when input is blocked"),
            self._r.render_variable("blocked_outputs_messaging", "string", "Message to return when output is blocked"),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Bedrock Guardrail."""
        parts = [
            self._r.render_output(
                "guardrail_id",
                f"aws_bedrock_guardrail.{instance.name}.id",
                "ID of the Bedrock Guardrail",
            ),
            self._r.render_output(
                "guardrail_arn",
                f"aws_bedrock_guardrail.{instance.name}.arn",
                "ARN of the Bedrock Guardrail",
            ),
        ]
        return "\n".join(parts)
