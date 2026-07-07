"""Aurora service generator — produces HCL for aws_rds_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class AuroraGenerator:
    """Generates Terraform files for Aurora (RDS) clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_rds_cluster resource."""
        attrs: dict = {"cluster_identifier": "var.cluster_identifier"}
        if instance.config.aurora_engine is not None:
            attrs["engine"] = "var.engine"
        if instance.config.aurora_master_username is not None:
            attrs["master_username"] = "var.master_username"

        return self._r.render_resource("aws_rds_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an Aurora cluster."""
        parts = [
            self._r.render_variable(
                "cluster_identifier", "string", "Identifier for the Aurora cluster"
            ),
        ]
        if instance.config.aurora_engine is not None:
            parts.append(
                self._r.render_variable(
                    "engine",
                    "string",
                    "Database engine for the Aurora cluster",
                    default=instance.config.aurora_engine,
                )
            )
        if instance.config.aurora_master_username is not None:
            parts.append(
                self._r.render_variable(
                    "master_username",
                    "string",
                    "Master username for the Aurora cluster",
                    default=instance.config.aurora_master_username,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an Aurora cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_rds_cluster.{instance.name}.arn",
                "ARN of the Aurora cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_rds_cluster.{instance.name}.endpoint",
                "Endpoint of the Aurora cluster",
            ),
        ]
        return "\n".join(parts)
