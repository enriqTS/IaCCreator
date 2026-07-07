"""MSK-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class MskConfig(BaseServiceConfig):
    """MSK-specific configuration."""

    service_type: Literal[ServiceType.MSK] = ServiceType.MSK
    msk_kafka_version: Optional[str] = None
    msk_number_of_broker_nodes: Optional[int] = None
