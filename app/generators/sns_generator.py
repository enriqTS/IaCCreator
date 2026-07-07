"""SNS service generator — produces HCL for aws_sns_topic resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.sns_config import SnsConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> SnsConfig:
    """Resolve typed SnsConfig, falling back to instance.config during migration.

    Once ResourceConfig is removed, this can be replaced with a direct
    get_typed_config(instance, SnsConfig) call.
    """
    if isinstance(instance.config, SnsConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class SNSGenerator:
    """Generates Terraform files for SNS topic resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate sns.tf with aws_sns_topic resource."""
        config = _resolve_config(instance)

        attrs: dict = {"name": "var.topic_name"}
        if config.display_name is not None:
            attrs["display_name"] = "var.display_name"
        if config.fifo_topic is not None:
            attrs["fifo_topic"] = "var.fifo_topic"
        if config.content_based_deduplication is not None:
            attrs["content_based_deduplication"] = "var.content_based_deduplication"
        if config.kms_master_key_id is not None:
            attrs["kms_master_key_id"] = "var.kms_master_key_id"
        if config.tags is not None:
            attrs["tags"] = "var.tags"
        return self._r.render_resource("aws_sns_topic", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an SNS instance."""
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable("topic_name", "string", "Name of the SNS topic"),
        ]
        if config.display_name is not None:
            parts.append(
                self._r.render_variable(
                    "display_name",
                    "string",
                    "Display name for the SNS topic",
                    default=config.display_name,
                )
            )
        if config.fifo_topic is not None:
            parts.append(
                self._r.render_variable(
                    "fifo_topic",
                    "bool",
                    "Whether the SNS topic is a FIFO topic",
                    default=config.fifo_topic,
                )
            )
        if config.content_based_deduplication is not None:
            parts.append(
                self._r.render_variable(
                    "content_based_deduplication",
                    "bool",
                    "Enable content-based deduplication for the SNS topic",
                    default=config.content_based_deduplication,
                )
            )
        if config.kms_master_key_id is not None:
            parts.append(
                self._r.render_variable(
                    "kms_master_key_id",
                    "string",
                    "ARN of the KMS key to use for encrypting SNS messages",
                    default=config.kms_master_key_id,
                )
            )
        if config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the SNS topic",
                )
            )
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
