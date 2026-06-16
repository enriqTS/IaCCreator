"""Bedrock Agent service generator — produces HCL for aws_bedrockagent_agent resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
from app.models.ir_models import ResourceInstanceIR


class BedrockAgentGenerator:
    """Generates Terraform files for Bedrock Agents."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_bedrockagent_agent resource."""
        attrs: dict = {
            "agent_name": "var.agent_name",
            "foundation_model": "var.foundation_model",
            "instruction": "var.instruction",
            "description": "var.description",
            "agent_resource_role_arn": "var.agent_resource_role_arn",
            "idle_session_ttl_in_seconds": "var.idle_session_ttl_in_seconds",
            "tags": "var.tags",
        }
        return self._r.render_resource("aws_bedrockagent_agent", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf dynamically from VARIABLE_SCHEMAS."""
        schema = VARIABLE_SCHEMAS[ServiceType.BEDROCK_AGENT]
        parts = []
        for entry in schema:
            tf_type = "map(string)" if entry.type == "map" else entry.type
            parts.append(self._r.render_variable(entry.name, tf_type, entry.description, entry.default))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Bedrock Agent."""
        parts = [
            self._r.render_output(
                "agent_id",
                f"aws_bedrockagent_agent.{instance.name}.agent_id",
                "ID of the Bedrock Agent",
            ),
            self._r.render_output(
                "agent_arn",
                f"aws_bedrockagent_agent.{instance.name}.agent_arn",
                "ARN of the Bedrock Agent",
            ),
        ]
        return "\n".join(parts)
