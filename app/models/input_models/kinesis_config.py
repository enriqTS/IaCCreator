"""Kinesis-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class KinesisConfig(BaseServiceConfig):
    """Kinesis-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.KINESIS] = ServiceType.KINESIS

    # Field order must match VARIABLE_SCHEMAS[ServiceType.KINESIS] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "stream_name",
        "shard_count",
    )

    # ── General ───────────────────────────────────────────────────────────
    stream_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Kinesis stream",
    )
    shard_count: int | None = TerraformField(
        None,
        group="General",
        description="Number of shards for the Kinesis stream",
    )
