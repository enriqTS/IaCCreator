"""Bedrock service generator — produces HCL for aws_bedrock_custom_model resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.bedrock_config import BedrockConfig
from app.models.ir_models import ResourceInstanceIR


class BedrockGenerator:
    """Generates Terraform files for Bedrock custom models."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_bedrock_custom_model resource."""
        get_typed_config(instance, BedrockConfig)

        attrs: dict = {
            "custom_model_name": "var.model_name",
            "base_model_identifier": "var.base_model_identifier",
            "role_arn": "var.role_arn",
            "training_data_config": {
                "s3_uri": "var.training_data_s3_uri",
            },
            "output_data_config": {
                "s3_uri": "var.output_data_s3_uri",
            },
            "hyperparameters": "var.hyperparameters",
            "tags": "var.tags",
        }
        return self._r.render_resource("aws_bedrock_custom_model", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf from typed config schema."""
        config_cls = type(get_typed_config(instance, BedrockConfig))
        schema = config_cls.get_variable_schema()
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
