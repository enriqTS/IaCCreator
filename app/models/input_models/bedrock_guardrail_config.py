"""Bedrock Guardrail-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockGuardrailConfig(BaseServiceConfig):
    """Bedrock Guardrail-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK_GUARDRAIL] = ServiceType.BEDROCK_GUARDRAIL
    bedrock_guardrail_name: str | None = None
