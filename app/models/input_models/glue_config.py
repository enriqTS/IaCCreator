"""Glue-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class GlueConfig(BaseServiceConfig):
    """Glue-specific configuration."""

    service_type: Literal[ServiceType.GLUE] = ServiceType.GLUE
    glue_catalog_database_name: Optional[str] = None
