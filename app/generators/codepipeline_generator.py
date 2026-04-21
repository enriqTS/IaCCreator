"""CodePipeline service generator — produces HCL for aws_codepipeline resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class CodePipelineGenerator:
    """Generates Terraform files for CodePipeline pipelines."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codepipeline resource."""
        attrs: dict = {"name": "var.pipeline_name"}
        if instance.config.codepipeline_role_arn is not None:
            attrs["role_arn"] = "var.role_arn"

        return self._r.render_resource("aws_codepipeline", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CodePipeline pipeline."""
        parts = [
            self._r.render_variable("pipeline_name", "string", "Name of the CodePipeline pipeline"),
        ]
        if instance.config.codepipeline_role_arn is not None:
            parts.append(self._r.render_variable(
                "role_arn", "string", "IAM role ARN for the CodePipeline pipeline",
                default=instance.config.codepipeline_role_arn,
            ))
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
