"""RDS service generator — produces HCL for aws_db_instance resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.rds_config import RdsConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> RdsConfig:
    """Resolve typed RdsConfig from the instance."""
    if isinstance(instance.config, RdsConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class RDSGenerator:
    """Generates Terraform files for RDS instances."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_db_instance resource."""
        config = _resolve_config(instance)
        attrs: dict = {"identifier": "var.db_identifier"}
        if config.engine is not None:
            attrs["engine"] = "var.engine"
        if config.instance_class is not None:
            attrs["instance_class"] = "var.instance_class"
        if config.allocated_storage is not None:
            attrs["allocated_storage"] = "var.allocated_storage"
        if config.username is not None:
            attrs["username"] = "var.username"

        return self._r.render_resource("aws_db_instance", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an RDS instance."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "db_identifier", "string", "Identifier for the RDS instance"
            ),
        ]
        if config.engine is not None:
            parts.append(
                self._r.render_variable(
                    "engine",
                    "string",
                    "Database engine type",
                    default=config.engine,
                )
            )
        if config.instance_class is not None:
            parts.append(
                self._r.render_variable(
                    "instance_class",
                    "string",
                    "RDS instance class",
                    default=config.instance_class,
                )
            )
        if config.allocated_storage is not None:
            parts.append(
                self._r.render_variable(
                    "allocated_storage",
                    "number",
                    "Allocated storage in GB",
                    default=config.allocated_storage,
                )
            )
        if config.username is not None:
            parts.append(
                self._r.render_variable(
                    "username",
                    "string",
                    "Master username for the database",
                    default=config.username,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an RDS instance."""
        parts = [
            self._r.render_output(
                "db_instance_arn",
                f"aws_db_instance.{instance.name}.arn",
                "ARN of the RDS instance",
            ),
            self._r.render_output(
                "db_instance_endpoint",
                f"aws_db_instance.{instance.name}.endpoint",
                "Endpoint of the RDS instance",
            ),
        ]
        return "\n".join(parts)
