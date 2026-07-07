"""CodeDeploy-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class CodeDeployConfig(BaseServiceConfig):
    """CodeDeploy-specific configuration."""

    service_type: Literal[ServiceType.CODEDEPLOY] = ServiceType.CODEDEPLOY
    codedeploy_compute_platform: Optional[str] = None
