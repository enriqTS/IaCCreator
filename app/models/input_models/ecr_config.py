"""ECR-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class EcrConfig(BaseServiceConfig):
    """ECR-specific configuration."""

    service_type: Literal[ServiceType.ECR] = ServiceType.ECR
    ecr_image_tag_mutability: str | None = None
    ecr_scan_on_push: bool | None = None
