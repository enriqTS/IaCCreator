"""EKS-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class EksConfig(BaseServiceConfig):
    """EKS-specific configuration."""

    service_type: Literal[ServiceType.EKS] = ServiceType.EKS
    eks_version: Optional[str] = None
    eks_endpoint_public_access: Optional[bool] = None
