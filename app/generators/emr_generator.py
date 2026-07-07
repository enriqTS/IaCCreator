"""EMR service generator — produces HCL for aws_emr_cluster resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.emr_config import EmrConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> EmrConfig:
    """Resolve typed EmrConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, EmrConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class EMRGenerator:
    """Generates Terraform files for EMR clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_emr_cluster resource."""
        config = _resolve_config(instance)
        attrs: dict = {"name": "var.cluster_name"}
        if config.release_label is not None:
            attrs["release_label"] = "var.release_label"
        if config.service_role is not None:
            attrs["service_role"] = "var.service_role"

        return self._r.render_resource("aws_emr_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an EMR cluster."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "cluster_name", "string", "Name of the EMR cluster"
            ),
        ]
        if config.release_label is not None:
            parts.append(
                self._r.render_variable(
                    "release_label",
                    "string",
                    "EMR release label",
                    default=config.release_label,
                )
            )
        if config.service_role is not None:
            parts.append(
                self._r.render_variable(
                    "service_role",
                    "string",
                    "IAM service role for the EMR cluster",
                    default=config.service_role,
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
