"""DocumentDB-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class DocumentDbConfig(BaseServiceConfig):
    """DocumentDB-specific configuration."""

    service_type: Literal[ServiceType.DOCUMENTDB] = ServiceType.DOCUMENTDB
    documentdb_master_username: str | None = None
