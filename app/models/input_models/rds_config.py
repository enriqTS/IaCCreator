"""RDS-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class RdsConfig(BaseServiceConfig):
    """RDS-specific configuration."""

    service_type: Literal[ServiceType.RDS] = ServiceType.RDS
    rds_engine: Optional[str] = None
    rds_instance_class: Optional[str] = None
    rds_allocated_storage: Optional[int] = None
    rds_username: Optional[str] = None
