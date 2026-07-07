"""Bedrock Knowledge Base-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BedrockKnowledgeBaseConfig(BaseServiceConfig):
    """Bedrock Knowledge Base-specific configuration."""

    service_type: Literal[ServiceType.BEDROCK_KNOWLEDGE_BASE] = ServiceType.BEDROCK_KNOWLEDGE_BASE
    bedrock_knowledge_base_name: Optional[str] = None
    bedrock_knowledge_base_embedding_model_arn: Optional[str] = None
