"""Bedrock AgentCore service generator — produces HCL for aws_bedrockagent_agent_runtime resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
from app.models.ir_models import ResourceInstanceIR


class BedrockAgentCoreGenerator:
    """Generates Terraform files for Bedrock AgentCore Runtime."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_bedrockagent_agent_runtime resource."""
        attrs: dict = {
            "agent_runtime_name": "var.agent_runtime_name",
            "foundation_model": "var.foundation_model",
            "role_arn": "var.role_arn",
            "description": "var.description",
            "memory_id": "var.memory_id",
            "idle_session_ttl": "var.idle_session_ttl",
        }
        return self._r.render_resource("aws_bedrockagent_agent_runtime", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Bedrock AgentCore Runtime."""
        schema = VARIABLE_SCHEMAS[ServiceType.BEDROCK_AGENTCORE]
        parts = []
        for entry in schema:
            tf_type = "map(string)" if entry.type == "map" else entry.type
            parts.append(self._r.render_variable(entry.name, tf_type, entry.description, entry.default))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Bedrock AgentCore Runtime."""
        parts = [
            self._r.render_output(
                "agent_runtime_arn",
                f"aws_bedrockagent_agent_runtime.{instance.name}.arn",
                "ARN of the Bedrock AgentCore Runtime",
            ),
            self._r.render_output(
                "agent_runtime_id",
                f"aws_bedrockagent_agent_runtime.{instance.name}.id",
                "ID of the Bedrock AgentCore Runtime",
            ),
        ]
        return "\n".join(parts)
