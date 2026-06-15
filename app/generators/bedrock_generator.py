"""Bedrock service generator — produces HCL for aws_bedrock_custom_model resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class BedrockGenerator:
    """Generates Terraform files for Bedrock custom models."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_bedrock_custom_model resource."""
        attrs: dict = {
            "custom_model_name": "var.model_name",
            "base_model_identifier": "var.base_model_identifier",
            "role_arn": "var.role_arn",
        }
        return self._r.render_resource("aws_bedrock_custom_model", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Bedrock custom model."""
        parts = [
            self._r.render_variable("model_name", "string", "Name of the custom model"),
            self._r.render_variable("base_model_identifier", "string", "Base model identifier for customization"),
            self._r.render_variable("role_arn", "string", "IAM role ARN for Bedrock"),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Bedrock custom model."""
        parts = [
            self._r.render_output(
                "model_arn",
                f"aws_bedrock_custom_model.{instance.name}.model_arn",
                "ARN of the Bedrock custom model",
            ),
            self._r.render_output(
                "model_name",
                f"aws_bedrock_custom_model.{instance.name}.custom_model_name",
                "Name of the Bedrock custom model",
            ),
        ]
        return "\n".join(parts)
