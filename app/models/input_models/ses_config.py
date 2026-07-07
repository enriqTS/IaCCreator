"""SES-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class SesConfig(BaseServiceConfig):
    """SES-specific configuration."""

    service_type: Literal[ServiceType.SES] = ServiceType.SES
    ses_domain: Optional[str] = None
