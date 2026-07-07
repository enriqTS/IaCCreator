"""EC2-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class Ec2Config(BaseServiceConfig):
    """EC2-specific configuration."""

    service_type: Literal[ServiceType.EC2] = ServiceType.EC2
    instance_type: Optional[str] = None
    ami: Optional[str] = None
    key_name: Optional[str] = None
