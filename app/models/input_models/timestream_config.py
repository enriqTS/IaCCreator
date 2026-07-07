"""Timestream-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class TimestreamConfig(BaseServiceConfig):
    """Timestream-specific configuration."""

    service_type: Literal[ServiceType.TIMESTREAM] = ServiceType.TIMESTREAM
    timestream_database_name: str | None = None
