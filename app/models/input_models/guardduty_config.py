from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class GuardDutyConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.GUARDDUTY] = ServiceType.GUARDDUTY
    enabled: bool = TerraformField(True, description="Enable GuardDuty monitoring")
    finding_publishing_frequency: str = TerraformField(
        "SIX_HOURS", description="Finding publishing frequency"
    )
