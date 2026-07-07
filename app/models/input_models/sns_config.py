"""SNS-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class SnsConfig(BaseServiceConfig):
    """SNS-specific configuration."""

    service_type: Literal[ServiceType.SNS] = ServiceType.SNS
    display_name: Optional[str] = None
    fifo_topic: Optional[bool] = None
    content_based_deduplication: Optional[bool] = None
    kms_master_key_id: Optional[str] = None
