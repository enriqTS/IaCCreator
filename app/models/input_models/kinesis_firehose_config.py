"""Kinesis Firehose-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class KinesisFirehoseConfig(BaseServiceConfig):
    """Kinesis Firehose-specific configuration."""

    service_type: Literal[ServiceType.KINESIS_FIREHOSE] = ServiceType.KINESIS_FIREHOSE
    firehose_destination: str | None = None
