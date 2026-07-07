"""CodeBuild-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CodeBuildConfig(BaseServiceConfig):
    """CodeBuild-specific configuration."""

    service_type: Literal[ServiceType.CODEBUILD] = ServiceType.CODEBUILD
    codebuild_source_type: str | None = None
    codebuild_service_role: str | None = None
