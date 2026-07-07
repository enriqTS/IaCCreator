"""AppStream-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class AppStreamConfig(BaseServiceConfig):
    """AppStream-specific configuration."""

    service_type: Literal[ServiceType.APPSTREAM] = ServiceType.APPSTREAM
    appstream_instance_type: str | None = None
