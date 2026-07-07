"""S3-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class S3Config(BaseServiceConfig):
    """S3-specific configuration."""

    service_type: Literal[ServiceType.S3] = ServiceType.S3
    versioning: Optional[bool] = None
    force_destroy: Optional[bool] = None
    object_lock_enabled: Optional[bool] = None
    acceleration_status: Optional[str] = None
