"""EMR service generator — produces HCL for aws_emr_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class EMRGenerator:
    """Generates Terraform files for EMR clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_emr_cluster resource."""
        attrs: dict = {"name": "var.cluster_name"}
        if instance.config.emr_release_label is not None:
            attrs["release_label"] = "var.release_label"
        if instance.config.emr_service_role is not None:
            attrs["service_role"] = "var.service_role"

        return self._r.render_resource("aws_emr_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an EMR cluster."""
        parts = [
            self._r.render_variable(
                "cluster_name", "string", "Name of the EMR cluster"
            ),
        ]
        if instance.config.emr_release_label is not None:
            parts.append(
                self._r.render_variable(
                    "release_label",
                    "string",
                    "EMR release label",
                    default=instance.config.emr_release_label,
                )
            )
        if instance.config.emr_service_role is not None:
            parts.append(
                self._r.render_variable(
                    "service_role",
                    "string",
                    "IAM service role for the EMR cluster",
                    default=instance.config.emr_service_role,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an EMR cluster."""
        parts = [
            self._r.render_output(
                "cluster_id",
                f"aws_emr_cluster.{instance.name}.id",
                "ID of the EMR cluster",
            ),
            self._r.render_output(
                "cluster_arn",
                f"aws_emr_cluster.{instance.name}.arn",
                "ARN of the EMR cluster",
            ),
        ]
        return "\n".join(parts)
