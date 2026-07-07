"""CloudWatch-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CloudWatchConfig(BaseServiceConfig):
    """CloudWatch-specific configuration."""

    service_type: Literal[ServiceType.CLOUDWATCH] = ServiceType.CLOUDWATCH
    retention_in_days: Optional[int] = None
    kms_key_id: Optional[str] = None
    log_group_class: Optional[str] = None
