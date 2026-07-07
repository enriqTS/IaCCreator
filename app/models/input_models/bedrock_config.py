"""Bedrock-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockConfig(BaseServiceConfig):
    """Bedrock-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK] = ServiceType.BEDROCK
    bedrock_model_name: Optional[str] = None
    bedrock_base_model_identifier: Optional[str] = None
