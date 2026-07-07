"""Kinesis service generator — produces HCL for aws_kinesis_stream resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.kinesis_config import KinesisConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> KinesisConfig:
    """Resolve typed KinesisConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, KinesisConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class KinesisGenerator:
    """Generates Terraform files for Kinesis streams."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_kinesis_stream resource."""
        config = _resolve_config(instance)
        attrs: dict = {"name": "var.stream_name"}
        if config.shard_count is not None:
            attrs["shard_count"] = "var.shard_count"

        return self._r.render_resource("aws_kinesis_stream", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Kinesis stream."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "stream_name", "string", "Name of the Kinesis stream"
            ),
        ]
        if config.shard_count is not None:
            parts.append(
                self._r.render_variable(
                    "shard_count",
                    "number",
                    "Number of shards for the Kinesis stream",
                    default=config.shard_count,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Kinesis stream."""
        parts = [
            self._r.render_output(
                "stream_arn",
                f"aws_kinesis_stream.{instance.name}.arn",
                "ARN of the Kinesis stream",
            ),
            self._r.render_output(
                "stream_name",
                f"aws_kinesis_stream.{instance.name}.name",
                "Name of the Kinesis stream",
            ),
        ]
        return "\n".join(parts)
