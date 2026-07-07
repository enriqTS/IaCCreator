"""SQS-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class SqsConfig(BaseServiceConfig):
    """SQS-specific configuration."""

    service_type: Literal[ServiceType.SQS] = ServiceType.SQS
    visibility_timeout_seconds: Optional[int] = None
    message_retention_seconds: Optional[int] = None
    fifo_queue: Optional[bool] = None
    delay_seconds: Optional[int] = None
    max_message_size: Optional[int] = None
    content_based_deduplication: Optional[bool] = None
