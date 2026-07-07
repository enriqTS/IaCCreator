"""CodePipeline-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CodePipelineConfig(BaseServiceConfig):
    """CodePipeline-specific configuration."""

    service_type: Literal[ServiceType.CODEPIPELINE] = ServiceType.CODEPIPELINE
    codepipeline_role_arn: str | None = None
