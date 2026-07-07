"""Bedrock-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockConfig(BaseServiceConfig):
    """Bedrock-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK] = ServiceType.BEDROCK
    bedrock_model_name: str | None = None
    bedrock_base_model_identifier: str | None = None
