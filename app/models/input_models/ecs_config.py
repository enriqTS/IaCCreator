"""ECS-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class EcsConfig(BaseServiceConfig):
    """ECS-specific configuration."""

    service_type: Literal[ServiceType.ECS] = ServiceType.ECS
    ecs_launch_type: Optional[str] = None
    ecs_desired_count: Optional[int] = None
    ecs_cpu: Optional[str] = None
    ecs_memory: Optional[str] = None
