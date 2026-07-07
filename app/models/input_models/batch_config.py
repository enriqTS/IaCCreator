"""Batch-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class BatchConfig(BaseServiceConfig):
    """Batch-specific configuration."""

    service_type: Literal[ServiceType.BATCH] = ServiceType.BATCH
    batch_compute_environment_type: str | None = None
    batch_max_vcpus: int | None = None
