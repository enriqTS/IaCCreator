"""CodePipeline service generator — produces HCL for aws_codepipeline resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.codepipeline_config import CodePipelineConfig
from app.models.ir_models import ResourceInstanceIR


class CodePipelineGenerator:
    """Generates Terraform files for CodePipeline pipelines."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codepipeline resource."""
        config = get_typed_config(instance, CodePipelineConfig)

        attrs: dict = {"name": Expr("var.pipeline_name")}
        if config.role_arn is not None:
            attrs["role_arn"] = Expr("var.role_arn")

        if config.artifact_bucket_name is not None:
            store = {"type": "S3", "location": Expr("var.artifact_bucket_name")}
            if config.artifact_kms_key_arn is not None:
                store["encryption_key"] = {
                    "id": Expr("var.artifact_kms_key_arn"),
                    "type": "KMS",
                }
            attrs["artifact_store"] = store
        if config.stages_json != "[]":
            action = {
                name: Expr(f"action.value.{name}")
                for name in [
                    "name",
                    "category",
                    "owner",
                    "provider",
                    "version",
                    "input_artifacts",
                    "output_artifacts",
                    "configuration",
                    "run_order",
                ]
            }
            action.update(
                {
                    name: Expr(f"try(action.value.{name}, null)")
                    for name in ["role_arn", "region"]
                }
            )
            attrs['dynamic "stage"'] = {
                "for_each": Expr("jsondecode(var.stages_json)"),
                "content": {
                    "name": Expr("stage.value.name"),
                    'dynamic "action"': {
                        "for_each": Expr("stage.value.actions"),
                        "content": action,
                    },
                },
            }
        if config._managed_artifacts:
            attrs["depends_on"] = Expr("[aws_iam_role_policy.artifacts]")
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
        if config.artifact_bucket_name is not None:
            parts.append(
                self._r.render_variable(
                    "artifact_bucket_name", "string", "S3 artifact bucket name"
                )
            )
        if config.artifact_kms_key_arn is not None:
            parts.append(
                self._r.render_variable(
                    "artifact_kms_key_arn", "string", "Artifact encryption key ARN"
                )
            )
        if config.stages_json != "[]":
            parts.append(
                self._r.render_variable(
                    "stages_json", "string", "Validated pipeline stages JSON"
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
