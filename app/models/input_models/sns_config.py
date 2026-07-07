"""SNS-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class SnsConfig(BaseServiceConfig):
    """SNS-specific configuration."""

    service_type: Literal[ServiceType.SNS] = ServiceType.SNS
    display_name: str | None = None
    fifo_topic: bool | None = None
    content_based_deduplication: bool | None = None
    kms_master_key_id: str | None = None
