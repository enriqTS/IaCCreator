"""SNS service generator — produces HCL for aws_sns_topic resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class SNSGenerator:
    """Generates Terraform files for SNS topic resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate sns.tf with aws_sns_topic resource."""
        attrs: dict = {"name": "var.topic_name"}
        if instance.config.display_name is not None:
            attrs["display_name"] = "var.display_name"
        if instance.config.fifo_topic is not None:
            attrs["fifo_topic"] = "var.fifo_topic"
        if instance.config.content_based_deduplication is not None:
            attrs["content_based_deduplication"] = "var.content_based_deduplication"
        if instance.config.kms_master_key_id is not None:
            attrs["kms_master_key_id"] = "var.kms_master_key_id"
        if instance.config.tags is not None:
            attrs["tags"] = "var.tags"
        return self._r.render_resource("aws_sns_topic", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an SNS instance."""
        parts = [
            self._r.render_variable("topic_name", "string", "Name of the SNS topic"),
        ]
        if instance.config.display_name is not None:
            parts.append(self._r.render_variable(
                "display_name", "string", "Display name for the SNS topic",
                default=instance.config.display_name,
            ))
        if instance.config.fifo_topic is not None:
            parts.append(self._r.render_variable(
                "fifo_topic", "bool", "Whether the SNS topic is a FIFO topic",
                default=instance.config.fifo_topic,
            ))
        if instance.config.content_based_deduplication is not None:
            parts.append(self._r.render_variable(
                "content_based_deduplication", "bool", "Enable content-based deduplication for the SNS topic",
                default=instance.config.content_based_deduplication,
            ))
        if instance.config.kms_master_key_id is not None:
            parts.append(self._r.render_variable(
                "kms_master_key_id", "string", "ARN of the KMS key to use for encrypting SNS messages",
                default=instance.config.kms_master_key_id,
            ))
        if instance.config.tags is not None:
            parts.append(self._r.render_variable(
                "tags", "map(string)", "Tags to apply to the SNS topic",
            ))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an SNS instance."""
        parts = [
            self._r.render_output(
                "topic_arn",
                f"aws_sns_topic.{instance.name}.arn",
                "ARN of the SNS topic",
            ),
            self._r.render_output(
                "topic_name",
                f"aws_sns_topic.{instance.name}.name",
                "Name of the SNS topic",
            ),
        ]
        return "\n".join(parts)
