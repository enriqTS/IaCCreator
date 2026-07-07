"""Kinesis Firehose-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class KinesisFirehoseConfig(BaseServiceConfig):
    """Kinesis Firehose-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.KINESIS_FIREHOSE] = ServiceType.KINESIS_FIREHOSE

    # Field order must match VARIABLE_SCHEMAS[ServiceType.KINESIS_FIREHOSE] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "stream_name",
        "destination",
    )

    # ── General ───────────────────────────────────────────────────────────
    stream_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Firehose delivery stream",
    )
    destination: str | None = TerraformField(
        None,
        group="General",
        description="Destination for the Firehose delivery stream",
    )
