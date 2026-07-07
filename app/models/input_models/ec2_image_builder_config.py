"""EC2 Image Builder-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class Ec2ImageBuilderConfig(BaseServiceConfig):
    """EC2 Image Builder-specific configuration."""

    service_type: Literal[ServiceType.EC2_IMAGE_BUILDER] = ServiceType.EC2_IMAGE_BUILDER
    imagebuilder_image_recipe_arn: Optional[str] = None
    imagebuilder_infrastructure_configuration_arn: Optional[str] = None
