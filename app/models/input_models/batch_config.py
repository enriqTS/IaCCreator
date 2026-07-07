"""Batch-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BatchConfig(BaseServiceConfig):
    """Batch-specific configuration."""

    service_type: Literal[ServiceType.BATCH] = ServiceType.BATCH
    batch_compute_environment_type: Optional[str] = None
    batch_max_vcpus: Optional[int] = None
