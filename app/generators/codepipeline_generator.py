"""CodePipeline service generator — produces HCL for aws_codepipeline resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.codepipeline_config import CodePipelineConfig
from app.models.ir_models import ResourceInstanceIR


class CodePipelineGenerator:
    """Generates Terraform files for CodePipeline pipelines."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codepipeline resource."""
        config = get_typed_config(instance, CodePipelineConfig)

        attrs: dict = {"name": "var.pipeline_name"}
        if config.role_arn is not None:
            attrs["role_arn"] = "var.role_arn"

        return self._r.render_resource("aws_codepipeline", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CodePipeline pipeline."""
        config = get_typed_config(instance, CodePipelineConfig)

        parts = [
            self._r.render_variable(
                "pipeline_name", "string", "Name of the CodePipeline pipeline"
            ),
        ]
        if config.role_arn is not None:
            parts.append(
                self._r.render_variable(
                    "role_arn",
                    "string",
                    "IAM role ARN for the CodePipeline pipeline",
                    default=config.role_arn,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a CodePipeline pipeline."""
        parts = [
            self._r.render_output(
                "pipeline_arn",
                f"aws_codepipeline.{instance.name}.arn",
                "ARN of the CodePipeline pipeline",
            ),
            self._r.render_output(
                "pipeline_name",
                f"aws_codepipeline.{instance.name}.name",
                "Name of the CodePipeline pipeline",
            ),
        ]
        return "\n".join(parts)
