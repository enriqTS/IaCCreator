"""Lambda-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class LambdaConfig(BaseServiceConfig):
    """Lambda-specific configuration."""

    service_type: Literal[ServiceType.LAMBDA] = ServiceType.LAMBDA
    handler: str | None = None
    runtime: str | None = None
    memory_size: int | None = None
    timeout: int | None = None
    is_layer: bool = False
    layers: list[str] | None = None
    architectures: str | None = None
    ephemeral_storage_size: int | None = None
    reserved_concurrent_executions: int | None = None
    publish: bool | None = None
