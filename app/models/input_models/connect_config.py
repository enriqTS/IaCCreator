"""Connect-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class ConnectConfig(BaseServiceConfig):
    """Connect-specific configuration."""

    service_type: Literal[ServiceType.CONNECT] = ServiceType.CONNECT
    connect_identity_management_type: Optional[str] = None
    connect_inbound_calls_enabled: Optional[bool] = None
    connect_outbound_calls_enabled: Optional[bool] = None
