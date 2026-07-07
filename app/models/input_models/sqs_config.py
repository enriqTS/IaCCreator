"""SQS-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class SqsConfig(BaseServiceConfig):
    """SQS-specific configuration."""

    service_type: Literal[ServiceType.SQS] = ServiceType.SQS
    visibility_timeout_seconds: int | None = None
    message_retention_seconds: int | None = None
    fifo_queue: bool | None = None
    delay_seconds: int | None = None
    max_message_size: int | None = None
    content_based_deduplication: bool | None = None
