"""DocumentDB service generator — produces HCL for aws_docdb_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class DocumentDBGenerator:
    """Generates Terraform files for DocumentDB clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_docdb_cluster resource."""
        attrs: dict = {"cluster_identifier": "var.cluster_identifier"}
        if instance.config.documentdb_master_username is not None:
            attrs["master_username"] = "var.master_username"

        return self._r.render_resource("aws_docdb_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a DocumentDB cluster."""
        parts = [
            self._r.render_variable(
                "cluster_identifier", "string", "Identifier for the DocumentDB cluster"
            ),
        ]
        if instance.config.documentdb_master_username is not None:
            parts.append(
                self._r.render_variable(
                    "master_username",
                    "string",
                    "Master username for the DocumentDB cluster",
                    default=instance.config.documentdb_master_username,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a DocumentDB cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_docdb_cluster.{instance.name}.arn",
                "ARN of the DocumentDB cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_docdb_cluster.{instance.name}.endpoint",
                "Endpoint of the DocumentDB cluster",
            ),
        ]
        return "\n".join(parts)
