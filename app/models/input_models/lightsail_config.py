"""Lightsail-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class LightsailConfig(BaseServiceConfig):
    """Lightsail-specific configuration."""

    service_type: Literal[ServiceType.LIGHTSAIL] = ServiceType.LIGHTSAIL
    lightsail_blueprint_id: str | None = None
    lightsail_bundle_id: str | None = None
    lightsail_availability_zone: str | None = None
