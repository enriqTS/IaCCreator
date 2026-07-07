"""SageMaker-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class SageMakerConfig(BaseServiceConfig):
    """SageMaker-specific configuration."""

    service_type: Literal[ServiceType.SAGEMAKER] = ServiceType.SAGEMAKER
    sagemaker_notebook_instance_name: Optional[str] = None
    sagemaker_instance_type: Optional[str] = None
