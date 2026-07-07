"""Athena-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class AthenaConfig(BaseServiceConfig):
    """Athena-specific configuration."""

    service_type: Literal[ServiceType.ATHENA] = ServiceType.ATHENA
    athena_name: Optional[str] = None
