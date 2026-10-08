"""AWS X-Ray trace group configuration model."""

from typing import Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class XRayConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.X_RAY] = ServiceType.X_RAY
    _managed_lambda_tracing: bool = PrivateAttr(default=False)
    _managed_ecs_tracing: bool = PrivateAttr(default=False)
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
