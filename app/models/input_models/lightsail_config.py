"""Lightsail-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class LightsailConfig(BaseServiceConfig):
    """Lightsail-specific configuration."""

    service_type: Literal[ServiceType.LIGHTSAIL] = ServiceType.LIGHTSAIL
    lightsail_blueprint_id: Optional[str] = None
    lightsail_bundle_id: Optional[str] = None
    lightsail_availability_zone: Optional[str] = None
