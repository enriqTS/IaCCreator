"""Timestream service generator — produces HCL for aws_timestreamwrite_database resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.timestream_config import TimestreamConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> TimestreamConfig:
    """Resolve typed TimestreamConfig from the instance."""
    if isinstance(instance.config, TimestreamConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class TimestreamGenerator:
    """Generates Terraform files for Timestream databases."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_timestreamwrite_database resource."""
        _resolve_config(instance)
        attrs: dict = {"database_name": "var.database_name"}

        return self._r.render_resource(
            "aws_timestreamwrite_database", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Timestream database."""
        _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "database_name", "string", "Name of the Timestream database"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Timestream database."""
        parts = [
            self._r.render_output(
                "database_arn",
                f"aws_timestreamwrite_database.{instance.name}.arn",
                "ARN of the Timestream database",
            ),
            self._r.render_output(
                "database_name",
                f"aws_timestreamwrite_database.{instance.name}.database_name",
                "Name of the Timestream database",
            ),
        ]
        return "\n".join(parts)
