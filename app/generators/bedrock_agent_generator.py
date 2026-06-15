"""Bedrock Agent service generator — produces HCL for aws_bedrockagent_agent resources."""

from app.generators.hcl_renderer import HCLRenderer
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
            "agent_resource_role_arn": "var.agent_resource_role_arn",
        }
        return self._r.render_resource("aws_bedrockagent_agent", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Bedrock Agent."""
        parts = [
            self._r.render_variable("agent_name", "string", "Name of the Bedrock Agent"),
            self._r.render_variable("foundation_model", "string", "Foundation model identifier for the agent"),
            self._r.render_variable("instruction", "string", "Instruction for the Bedrock Agent"),
            self._r.render_variable("agent_resource_role_arn", "string", "IAM role ARN for the Bedrock Agent"),
        ]
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
