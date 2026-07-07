"""S3-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class S3Config(BaseServiceConfig):
    """S3-specific configuration."""

    service_type: Literal[ServiceType.S3] = ServiceType.S3
    versioning: bool | None = None
    force_destroy: bool | None = None
    object_lock_enabled: bool | None = None
    acceleration_status: str | None = None
