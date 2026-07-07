"""Bedrock Agent-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockAgentConfig(BaseServiceConfig):
    """Bedrock Agent-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK_AGENT] = ServiceType.BEDROCK_AGENT
    bedrock_agent_name: Optional[str] = None
    bedrock_agent_foundation_model: Optional[str] = None
    bedrock_agent_instruction: Optional[str] = None
