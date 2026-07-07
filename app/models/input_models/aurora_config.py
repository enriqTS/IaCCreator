"""Aurora-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class AuroraConfig(BaseServiceConfig):
    """Aurora-specific configuration."""

    service_type: Literal[ServiceType.AURORA] = ServiceType.AURORA
    aurora_engine: Optional[str] = None
    aurora_master_username: Optional[str] = None
