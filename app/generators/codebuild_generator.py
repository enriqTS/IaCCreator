"""CodeBuild service generator — produces HCL for aws_codebuild_project resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class CodeBuildGenerator:
    """Generates Terraform files for CodeBuild projects."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codebuild_project resource."""
        attrs: dict = {"name": "var.project_name"}
        if instance.config.codebuild_service_role is not None:
            attrs["service_role"] = "var.service_role"

        source_block: dict = {}
        if instance.config.codebuild_source_type is not None:
            source_block["type"] = "var.source_type"
        if source_block:
            attrs["source"] = source_block

        return self._r.render_resource("aws_codebuild_project", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CodeBuild project."""
        parts = [
            self._r.render_variable(
                "project_name", "string", "Name of the CodeBuild project"
            ),
        ]
        if instance.config.codebuild_service_role is not None:
            parts.append(
                self._r.render_variable(
                    "service_role",
                    "string",
                    "IAM service role ARN for the CodeBuild project",
                    default=instance.config.codebuild_service_role,
                )
            )
        if instance.config.codebuild_source_type is not None:
            parts.append(
                self._r.render_variable(
                    "source_type",
                    "string",
                    "Source type for the CodeBuild project",
                    default=instance.config.codebuild_source_type,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a CodeBuild project."""
        parts = [
            self._r.render_output(
                "project_arn",
                f"aws_codebuild_project.{instance.name}.arn",
                "ARN of the CodeBuild project",
            ),
            self._r.render_output(
                "project_name",
                f"aws_codebuild_project.{instance.name}.name",
                "Name of the CodeBuild project",
            ),
        ]
        return "\n".join(parts)
