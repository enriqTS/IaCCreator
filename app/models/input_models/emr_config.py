"""EMR-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class EmrConfig(BaseServiceConfig):
    """EMR-specific configuration."""

    service_type: Literal[ServiceType.EMR] = ServiceType.EMR
    emr_release_label: str | None = None
    emr_service_role: str | None = None
