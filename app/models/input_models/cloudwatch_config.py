"""CloudWatch-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CloudWatchConfig(BaseServiceConfig):
    """CloudWatch-specific configuration."""

    service_type: Literal[ServiceType.CLOUDWATCH] = ServiceType.CLOUDWATCH
    retention_in_days: int | None = None
    kms_key_id: str | None = None
    log_group_class: str | None = None
