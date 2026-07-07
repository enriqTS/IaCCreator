"""Amazon Q-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class AmazonQConfig(BaseServiceConfig):
    """Amazon Q-specific configuration."""

    service_type: Literal[ServiceType.AMAZON_Q] = ServiceType.AMAZON_Q
    amazon_q_application_name: Optional[str] = None
