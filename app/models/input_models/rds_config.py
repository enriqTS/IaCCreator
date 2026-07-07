"""RDS-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class RdsConfig(BaseServiceConfig):
    """RDS-specific configuration."""

    service_type: Literal[ServiceType.RDS] = ServiceType.RDS
    rds_engine: str | None = None
    rds_instance_class: str | None = None
    rds_allocated_storage: int | None = None
    rds_username: str | None = None
