"""App Runner-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class AppRunnerConfig(BaseServiceConfig):
    """App Runner-specific configuration."""

    service_type: Literal[ServiceType.APP_RUNNER] = ServiceType.APP_RUNNER
    apprunner_source_type: str | None = None
    apprunner_image_identifier: str | None = None
