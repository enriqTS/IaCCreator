"""EMR-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class EmrConfig(BaseServiceConfig):
    """EMR-specific configuration."""

    service_type: Literal[ServiceType.EMR] = ServiceType.EMR
    emr_release_label: Optional[str] = None
    emr_service_role: Optional[str] = None
