"""Redshift-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class RedshiftConfig(BaseServiceConfig):
    """Redshift-specific configuration."""

    service_type: Literal[ServiceType.REDSHIFT] = ServiceType.REDSHIFT
    redshift_node_type: Optional[str] = None
    redshift_master_username: Optional[str] = None
