"""Kinesis Firehose service generator — produces HCL for aws_kinesis_firehose_delivery_stream resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.kinesis_firehose_config import KinesisFirehoseConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> KinesisFirehoseConfig:
    """Resolve typed KinesisFirehoseConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, KinesisFirehoseConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class KinesisFirehoseGenerator:
    """Generates Terraform files for Kinesis Firehose delivery streams."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_kinesis_firehose_delivery_stream resource."""
        config = _resolve_config(instance)
        attrs: dict = {"name": Expr("var.stream_name")}
        if config.destination is not None:
            attrs["destination"] = Expr("var.destination")

        if config.bucket_arn is not None:
            attrs["extended_s3_configuration"] = {
                "role_arn": Expr("var.role_arn"),
                "bucket_arn": Expr("var.bucket_arn"),
                "prefix": Expr("var.s3_prefix"),
            }
        if config._managed_s3_destination:
            attrs["depends_on"] = Expr("[aws_iam_role_policy.s3_delivery]")
        return self._r.render_resource(
            "aws_kinesis_firehose_delivery_stream", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Kinesis Firehose delivery stream."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "stream_name", "string", "Name of the Kinesis Firehose delivery stream"
            ),
        ]
        if config.destination is not None:
            parts.append(
                self._r.render_variable(
                    "destination",
                    "string",
                    "Destination for the Kinesis Firehose delivery stream",
                    default=config.destination,
                )
            )
        if config.bucket_arn is not None:
            parts.extend(
                self._r.render_variable(name, "string", description)
                for name, description in [
                    ("role_arn", "Firehose delivery role ARN"),
                    ("bucket_arn", "S3 destination bucket ARN"),
                    ("s3_prefix", "Delivery object prefix"),
                ]
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Kinesis Firehose delivery stream."""
        parts = [
            self._r.render_output(
                "delivery_stream_arn",
                f"aws_kinesis_firehose_delivery_stream.{instance.name}.arn",
                "ARN of the Kinesis Firehose delivery stream",
            ),
            self._r.render_output(
                "delivery_stream_name",
                f"aws_kinesis_firehose_delivery_stream.{instance.name}.name",
                "Name of the Kinesis Firehose delivery stream",
            ),
        ]
        return "\n".join(parts)
