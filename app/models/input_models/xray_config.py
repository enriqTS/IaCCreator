"""AWS X-Ray trace group configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class XRayConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.X_RAY] = ServiceType.X_RAY
    group_name: str = TerraformField(
        "application-traces", description="X-Ray group name"
    )
    filter_expression: str = TerraformField(
        "responsetime > 5", description="Trace filter expression"
    )
    insights_enabled: bool = TerraformField(False, description="Enable X-Ray Insights")
    notifications_enabled: bool = TerraformField(
        False, description="Enable Insights notifications"
    )
