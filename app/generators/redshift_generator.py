"""Redshift service generator — produces HCL for aws_redshift_cluster resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.redshift_config import RedshiftConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> RedshiftConfig:
    """Resolve typed RedshiftConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, RedshiftConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class RedshiftGenerator:
    """Generates Terraform files for Redshift clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_redshift_cluster resource."""
        config = _resolve_config(instance)
        attrs: dict = {"cluster_identifier": "var.cluster_identifier"}
        if config.node_type is not None:
            attrs["node_type"] = "var.node_type"
        if config.master_username is not None:
            attrs["master_username"] = "var.master_username"

        return self._r.render_resource("aws_redshift_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Redshift cluster."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "cluster_identifier", "string", "Identifier for the Redshift cluster"
            ),
        ]
        if config.node_type is not None:
            parts.append(
                self._r.render_variable(
                    "node_type",
                    "string",
                    "Node type for the Redshift cluster",
                    default=config.node_type,
                )
            )
        if config.master_username is not None:
            parts.append(
                self._r.render_variable(
                    "master_username",
                    "string",
                    "Master username for the Redshift cluster",
                    default=config.master_username,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Redshift cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_redshift_cluster.{instance.name}.arn",
                "ARN of the Redshift cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_redshift_cluster.{instance.name}.endpoint",
                "Endpoint of the Redshift cluster",
            ),
        ]
        return "\n".join(parts)
