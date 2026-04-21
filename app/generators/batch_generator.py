"""Batch service generator — produces HCL for aws_batch_compute_environment resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class BatchGenerator:
    """Generates Terraform files for AWS Batch compute environments."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_batch_compute_environment resource."""
        attrs: dict = {
            "compute_environment_name": "var.compute_environment_name",
            "service_role": "var.service_role_arn",
        }
        if instance.config.batch_compute_environment_type is not None:
            attrs["type"] = "var.batch_compute_environment_type"
        if instance.config.batch_max_vcpus is not None:
            attrs["compute_resources"] = {"max_vcpus": "var.batch_max_vcpus"}

        return self._r.render_resource("aws_batch_compute_environment", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Batch compute environment."""
        parts = [
            self._r.render_variable("compute_environment_name", "string", "Name of the Batch compute environment"),
            self._r.render_variable("service_role_arn", "string", "ARN of the IAM service role for Batch"),
        ]
        if instance.config.batch_compute_environment_type is not None:
            parts.append(self._r.render_variable(
                "batch_compute_environment_type", "string", "Type of the Batch compute environment",
                default=instance.config.batch_compute_environment_type,
            ))
        if instance.config.batch_max_vcpus is not None:
            parts.append(self._r.render_variable(
                "batch_max_vcpus", "number", "Maximum vCPUs for the Batch compute resources",
                default=instance.config.batch_max_vcpus,
            ))
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
                f"aws_batch_compute_environment.{instance.name}.compute_environment_name",
                "Name of the Batch compute environment",
            ),
        ]
        return "\n".join(parts)
