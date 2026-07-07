"""SQS service generator — produces HCL for aws_sqs_queue resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class SQSGenerator:
    """Generates Terraform files for SQS queue resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate sqs.tf with aws_sqs_queue resource."""
        attrs: dict = {"name": "var.queue_name"}
        if instance.config.visibility_timeout_seconds is not None:
            attrs["visibility_timeout_seconds"] = "var.visibility_timeout_seconds"
        if instance.config.message_retention_seconds is not None:
            attrs["message_retention_seconds"] = "var.message_retention_seconds"
        if instance.config.fifo_queue is not None:
            attrs["fifo_queue"] = "var.fifo_queue"
        if instance.config.content_based_deduplication is not None:
            attrs["content_based_deduplication"] = "var.content_based_deduplication"
        if instance.config.delay_seconds is not None:
            attrs["delay_seconds"] = "var.delay_seconds"
        if instance.config.max_message_size is not None:
            attrs["max_message_size"] = "var.max_message_size"
        if instance.config.tags is not None:
            attrs["tags"] = "var.tags"
        return self._r.render_resource("aws_sqs_queue", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an SQS instance."""
        parts = [
            self._r.render_variable("queue_name", "string", "Name of the SQS queue"),
        ]
        if instance.config.visibility_timeout_seconds is not None:
            parts.append(
                self._r.render_variable(
                    "visibility_timeout_seconds",
                    "number",
                    "The visibility timeout for the queue in seconds",
                    default=instance.config.visibility_timeout_seconds,
                )
            )
        if instance.config.message_retention_seconds is not None:
            parts.append(
                self._r.render_variable(
                    "message_retention_seconds",
                    "number",
                    "The number of seconds to retain a message",
                    default=instance.config.message_retention_seconds,
                )
            )
        if instance.config.fifo_queue is not None:
            parts.append(
                self._r.render_variable(
                    "fifo_queue",
                    "bool",
                    "Whether the SQS queue is a FIFO queue",
                    default=instance.config.fifo_queue,
                )
            )
        if instance.config.content_based_deduplication is not None:
            parts.append(
                self._r.render_variable(
                    "content_based_deduplication",
                    "bool",
                    "Enable content-based deduplication for the SQS queue",
                    default=instance.config.content_based_deduplication,
                )
            )
        if instance.config.delay_seconds is not None:
            parts.append(
                self._r.render_variable(
                    "delay_seconds",
                    "number",
                    "The time in seconds that delivery of all messages is delayed",
                    default=instance.config.delay_seconds,
                )
            )
        if instance.config.max_message_size is not None:
            parts.append(
                self._r.render_variable(
                    "max_message_size",
                    "number",
                    "The limit of how many bytes a message can contain",
                    default=instance.config.max_message_size,
                )
            )
        if instance.config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the SQS queue",
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an SQS instance."""
        parts = [
            self._r.render_output(
                "queue_arn",
                f"aws_sqs_queue.{instance.name}.arn",
                "ARN of the SQS queue",
            ),
            self._r.render_output(
                "queue_url",
                f"aws_sqs_queue.{instance.name}.url",
                "URL of the SQS queue",
            ),
        ]
        return "\n".join(parts)
