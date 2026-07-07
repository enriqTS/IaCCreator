"""Amplify-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class AmplifyConfig(BaseServiceConfig):
    """Amplify-specific configuration."""

    service_type: Literal[ServiceType.AMPLIFY] = ServiceType.AMPLIFY
    amplify_name: str | None = None
