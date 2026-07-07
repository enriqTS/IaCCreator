"""SQS-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class SqsConfig(BaseServiceConfig):
    """SQS-specific configuration."""

    service_type: Literal[ServiceType.SQS] = ServiceType.SQS

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "queue_name",
        "fifo_queue",
        "visibility_timeout_seconds",
        "message_retention_seconds",
        "delay_seconds",
        "max_message_size",
        "content_based_deduplication",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    queue_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the SQS queue",
    )
    fifo_queue: bool | None = TerraformField(
        None,
        group="General",
        description="Whether the SQS queue is a FIFO queue",
    )

    # ── Configuration ─────────────────────────────────────────────────────
    visibility_timeout_seconds: int | None = TerraformField(
        None,
        group="Configuration",
        description="The visibility timeout for the queue in seconds",
        validation=ValidationRule(min=0, max=43200),
    )
    message_retention_seconds: int | None = TerraformField(
        None,
        group="Configuration",
        description="The number of seconds to retain a message",
        validation=ValidationRule(min=60, max=1209600),
    )
    delay_seconds: int | None = TerraformField(
        None,
        group="Configuration",
        description="The time in seconds that delivery of all messages is delayed",
        validation=ValidationRule(min=0, max=900),
    )
    max_message_size: int | None = TerraformField(
        None,
        group="Configuration",
        description="The limit of how many bytes a message can contain",
        validation=ValidationRule(min=1024, max=262144),
    )
    content_based_deduplication: bool | None = TerraformField(
        None,
        group="Configuration",
        description="Enable content-based deduplication for the SQS queue",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the SQS queue",
        tf_type="map",
    )
