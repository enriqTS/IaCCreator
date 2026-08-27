from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class SecurityHubConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.SECURITY_HUB] = ServiceType.SECURITY_HUB
    enable_default_standards: bool = TerraformField(
        True, description="Enable default security standards"
    )
    control_finding_generator: str = TerraformField(
        "SECURITY_CONTROL", description="Finding generator mode"
    )
