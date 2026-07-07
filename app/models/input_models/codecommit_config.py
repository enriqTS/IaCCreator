"""CodeCommit-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CodeCommitConfig(BaseServiceConfig):
    """CodeCommit-specific configuration."""

    service_type: Literal[ServiceType.CODECOMMIT] = ServiceType.CODECOMMIT
    codecommit_repository_name: Optional[str] = None
