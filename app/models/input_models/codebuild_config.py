"""CodeBuild-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CodeBuildConfig(BaseServiceConfig):
    """CodeBuild-specific configuration."""

    service_type: Literal[ServiceType.CODEBUILD] = ServiceType.CODEBUILD
    codebuild_source_type: Optional[str] = None
    codebuild_service_role: Optional[str] = None
