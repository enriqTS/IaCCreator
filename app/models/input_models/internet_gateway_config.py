"""Internet gateway configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class InternetGatewayConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.INTERNET_GATEWAY] = ServiceType.INTERNET_GATEWAY
    vpc_id: str = TerraformField("", description="VPC ID")
