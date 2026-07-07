"""Kinesis-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class KinesisConfig(BaseServiceConfig):
    """Kinesis-specific configuration."""

    service_type: Literal[ServiceType.KINESIS] = ServiceType.KINESIS
    kinesis_shard_count: int | None = None
