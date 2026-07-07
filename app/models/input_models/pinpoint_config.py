"""Pinpoint-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class PinpointConfig(BaseServiceConfig):
    """Pinpoint-specific configuration."""

    service_type: Literal[ServiceType.PINPOINT] = ServiceType.PINPOINT
    pinpoint_name: str | None = None
