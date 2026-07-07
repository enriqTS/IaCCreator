"""CodePipeline-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CodePipelineConfig(BaseServiceConfig):
    """CodePipeline-specific configuration."""

    service_type: Literal[ServiceType.CODEPIPELINE] = ServiceType.CODEPIPELINE
    codepipeline_role_arn: Optional[str] = None
