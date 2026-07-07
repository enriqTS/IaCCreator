"""CloudSearch-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CloudSearchConfig(BaseServiceConfig):
    """CloudSearch-specific configuration."""

    service_type: Literal[ServiceType.CLOUDSEARCH] = ServiceType.CLOUDSEARCH
    cloudsearch_name: str | None = None
