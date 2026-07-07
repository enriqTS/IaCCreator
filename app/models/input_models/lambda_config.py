"""Lambda-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class LambdaConfig(BaseServiceConfig):
    """Lambda-specific configuration."""

    service_type: Literal[ServiceType.LAMBDA] = ServiceType.LAMBDA
    handler: Optional[str] = None
    runtime: Optional[str] = None
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    is_layer: bool = False
    layers: Optional[list[str]] = None
    architectures: Optional[str] = None
    ephemeral_storage_size: Optional[int] = None
    reserved_concurrent_executions: Optional[int] = None
    publish: Optional[bool] = None
