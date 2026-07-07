"""SNS-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class SnsConfig(BaseServiceConfig):
    """SNS-specific configuration."""

    service_type: Literal[ServiceType.SNS] = ServiceType.SNS

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "topic_name",
        "display_name",
        "fifo_topic",
        "content_based_deduplication",
        "kms_master_key_id",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    topic_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the SNS topic",
    )
    display_name: str | None = TerraformField(
        None,
        group="General",
        description="Display name for the SNS topic",
    )

    # ── Configuration ─────────────────────────────────────────────────────
    fifo_topic: bool | None = TerraformField(
        None,
        group="Configuration",
        description="Whether the SNS topic is a FIFO topic",
    )
    content_based_deduplication: bool | None = TerraformField(
        None,
        group="Configuration",
        description="Enable content-based deduplication for the SNS topic",
    )
    kms_master_key_id: str | None = TerraformField(
        None,
        group="Configuration",
        description="ARN of the KMS key to use for encrypting SNS messages",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the SNS topic",
        tf_type="map",
    )
