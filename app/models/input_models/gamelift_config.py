"""GameLift-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class GameLiftConfig(BaseServiceConfig):
    """GameLift-specific configuration."""

    service_type: Literal[ServiceType.GAMELIFT] = ServiceType.GAMELIFT
    gamelift_ec2_instance_type: Optional[str] = None
