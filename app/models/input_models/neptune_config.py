"""Neptune-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class NeptuneConfig(BaseServiceConfig):
    """Neptune-specific configuration."""

    service_type: Literal[ServiceType.NEPTUNE] = ServiceType.NEPTUNE
    neptune_cluster_identifier: str | None = None
