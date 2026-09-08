"""CodeBuild service generator — produces HCL for aws_codebuild_project resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.codebuild_config import CodeBuildConfig
from app.models.ir_models import ResourceInstanceIR


class CodeBuildGenerator:
    """Generates Terraform files for CodeBuild projects."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codebuild_project resource."""
        config = get_typed_config(instance, CodeBuildConfig)

        attrs: dict = {
            "name": Expr("var.project_name"),
            "service_role": Expr("var.service_role"),
            "artifacts": {"type": "NO_ARTIFACTS"},
            "environment": {
                "type": "LINUX_CONTAINER",
                "image": Expr("var.image"),
                "compute_type": Expr("var.compute_type"),
            },
        }
        if config._inject_runtime_secrets:
            attrs["environment"]['dynamic "environment_variable"'] = {
                "for_each": Expr("local.runtime_secrets"),
                "content": {
                    "name": Expr("environment_variable.key"),
                    "value": Expr("environment_variable.value"),
                    "type": "SECRETS_MANAGER",
                },
            }
            attrs["depends_on"] = Expr("[aws_iam_role_policy.runtime_secrets]")

        source_block: dict = {"type": "NO_SOURCE", "buildspec": Expr("var.buildspec")}
        if config.source_type is not None:
            source_block["type"] = Expr("var.source_type")
        if source_block:
            attrs["source"] = source_block

        return self._r.render_resource("aws_codebuild_project", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CodeBuild project."""
        config = get_typed_config(instance, CodeBuildConfig)

        parts = [
            self._r.render_variable(
                "project_name", "string", "Name of the CodeBuild project"
            ),
        ]
        for name in ("service_role", "image", "compute_type", "buildspec"):
            parts.append(
                self._r.render_variable(
                    name,
                    "string",
                    name.replace("_", " "),
                    default=getattr(config, name),
                )
            )
        if config.source_type is not None:
            parts.append(
                self._r.render_variable(
                    "source_type",
                    "string",
                    "Source type for the CodeBuild project",
                    default=config.source_type,
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
