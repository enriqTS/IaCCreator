"""Bedrock AgentCore-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockAgentcoreConfig(BaseServiceConfig):
    """Bedrock AgentCore-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK_AGENTCORE] = ServiceType.BEDROCK_AGENTCORE
