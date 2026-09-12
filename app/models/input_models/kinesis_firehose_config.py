"""Kinesis Firehose-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class KinesisFirehoseConfig(BaseServiceConfig):
    """Kinesis Firehose-specific configuration — single source of truth."""

    _managed_s3_destination: bool = PrivateAttr(default=False)
    role_arn: str | None = TerraformField(
        None, description="External Firehose delivery role ARN"
    )
    bucket_arn: str | None = TerraformField(
        None, description="S3 destination bucket ARN"
    )
    s3_prefix: str = TerraformField("", description="S3 delivery object prefix")

    service_type: Literal[ServiceType.KINESIS_FIREHOSE] = ServiceType.KINESIS_FIREHOSE

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
