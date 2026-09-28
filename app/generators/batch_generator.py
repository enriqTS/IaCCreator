"""Batch service generator — produces HCL for aws_batch_compute_environment resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.batch_config import BatchConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> BatchConfig:
    """Resolve typed BatchConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, BatchConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class BatchGenerator:
    """Generates Terraform files for AWS Batch compute environments."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_batch_compute_environment resource."""
        config = _resolve_config(instance)

        attrs: dict = {
            "name": Expr("var.compute_environment_name"),
            "service_role": Expr("var.service_role_arn"),
        }
        if config.batch_compute_environment_type is not None:
            attrs["type"] = Expr("var.batch_compute_environment_type")
        if config.batch_max_vcpus is not None:
            attrs["compute_resources"] = {"max_vcpus": Expr("var.batch_max_vcpus")}

        result = self._r.render_resource(
            "aws_batch_compute_environment", instance.name, attrs
        )
        if config.job_queue_name:
            result += "\n" + self._r.render_resource(
                "aws_batch_job_queue",
                f"{instance.name}_queue",
                {
                    "name": Expr("var.job_queue_name"),
                    "state": "ENABLED",
                    "priority": Expr("var.job_queue_priority"),
                    "compute_environment_order": {
                        "order": 1,
                        "compute_environment": Expr(
                            f"aws_batch_compute_environment.{instance.name}.arn"
                        ),
                    },
                },
            )
        return result

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Batch compute environment."""
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable(
                "compute_environment_name",
                "string",
                "Name of the Batch compute environment",
            ),
            self._r.render_variable(
                "service_role_arn", "string", "ARN of the IAM service role for Batch"
            ),
        ]
        if config.batch_compute_environment_type is not None:
            parts.append(
                self._r.render_variable(
                    "batch_compute_environment_type",
                    "string",
                    "Type of the Batch compute environment",
                    default=config.batch_compute_environment_type,
                )
            )
        if config.batch_max_vcpus is not None:
            parts.append(
                self._r.render_variable(
                    "batch_max_vcpus",
                    "number",
                    "Maximum vCPUs for the Batch compute resources",
                    default=config.batch_max_vcpus,
                )
            )
        if config.job_queue_name:
            parts.extend(
                [
                    self._r.render_variable(
                        "job_queue_name",
                        "string",
                        "Name of the Batch job queue",
                        default=config.job_queue_name,
                    ),
                    self._r.render_variable(
                        "job_queue_priority",
                        "number",
                        "Priority of the Batch job queue",
                        default=config.job_queue_priority,
                    ),
                ]
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Batch compute environment."""
        parts = [
            self._r.render_output(
                "compute_environment_arn",
                f"aws_batch_compute_environment.{instance.name}.arn",
                "ARN of the Batch compute environment",
            ),
            self._r.render_output(
                "compute_environment_name",
                f"aws_batch_compute_environment.{instance.name}.name",
                "Name of the Batch compute environment",
            ),
        ]
        if _resolve_config(instance).job_queue_name:
            parts.append(
                self._r.render_output(
                    "job_queue_arn",
                    f"aws_batch_job_queue.{instance.name}_queue.arn",
                    "ARN of the Batch job queue",
                )
            )
        return "\n".join(parts)
