"""Bedrock Agent-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockAgentConfig(BaseServiceConfig):
    """Bedrock Agent-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK_AGENT] = ServiceType.BEDROCK_AGENT
    bedrock_agent_name: str | None = None
    bedrock_agent_foundation_model: str | None = None
    bedrock_agent_instruction: str | None = None
