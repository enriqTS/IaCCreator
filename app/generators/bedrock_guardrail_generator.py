"""Bedrock Guardrail service generator — produces HCL for aws_bedrock_guardrail resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
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
            "content_policy_config": {
                "filters_config": {
                    "type": "VIOLENCE",
                    "input_strength": "var.content_policy_strength",
                    "output_strength": "var.content_policy_strength",
                },
            },
            "tags": "var.tags",
        }
        return self._r.render_resource("aws_bedrock_guardrail", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf dynamically from VARIABLE_SCHEMAS."""
        schema = VARIABLE_SCHEMAS[ServiceType.BEDROCK_GUARDRAIL]
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
