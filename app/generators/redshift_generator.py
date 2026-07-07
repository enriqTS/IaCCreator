"""Redshift service generator — produces HCL for aws_redshift_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class RedshiftGenerator:
    """Generates Terraform files for Redshift clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_redshift_cluster resource."""
        attrs: dict = {"cluster_identifier": "var.cluster_identifier"}
        if instance.config.redshift_node_type is not None:
            attrs["node_type"] = "var.node_type"
        if instance.config.redshift_master_username is not None:
            attrs["master_username"] = "var.master_username"

        return self._r.render_resource("aws_redshift_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Redshift cluster."""
        parts = [
            self._r.render_variable(
                "cluster_identifier", "string", "Identifier for the Redshift cluster"
            ),
        ]
        if instance.config.redshift_node_type is not None:
            parts.append(
                self._r.render_variable(
                    "node_type",
                    "string",
                    "Node type for the Redshift cluster",
                    default=instance.config.redshift_node_type,
                )
            )
        if instance.config.redshift_master_username is not None:
            parts.append(
                self._r.render_variable(
                    "master_username",
                    "string",
                    "Master username for the Redshift cluster",
                    default=instance.config.redshift_master_username,
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
