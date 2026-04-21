"""Kinesis Firehose service generator — produces HCL for aws_kinesis_firehose_delivery_stream resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class KinesisFirehoseGenerator:
    """Generates Terraform files for Kinesis Firehose delivery streams."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_kinesis_firehose_delivery_stream resource."""
        attrs: dict = {"name": "var.stream_name"}
        if instance.config.firehose_destination is not None:
            attrs["destination"] = "var.destination"

        return self._r.render_resource("aws_kinesis_firehose_delivery_stream", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Kinesis Firehose delivery stream."""
        parts = [
            self._r.render_variable("stream_name", "string", "Name of the Kinesis Firehose delivery stream"),
        ]
        if instance.config.firehose_destination is not None:
            parts.append(self._r.render_variable(
                "destination", "string", "Destination for the Kinesis Firehose delivery stream",
                default=instance.config.firehose_destination,
            ))
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
