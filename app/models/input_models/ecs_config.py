"""ECS-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class EcsConfig(BaseServiceConfig):
    """ECS-specific configuration."""

    service_type: Literal[ServiceType.ECS] = ServiceType.ECS
    ecs_launch_type: str | None = None
    ecs_desired_count: int | None = None
    ecs_cpu: str | None = None
    ecs_memory: str | None = None
