"""EC2-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class Ec2Config(BaseServiceConfig):
    """EC2-specific configuration."""

    service_type: Literal[ServiceType.EC2] = ServiceType.EC2
    instance_type: str | None = None
    ami: str | None = None
    key_name: str | None = None
