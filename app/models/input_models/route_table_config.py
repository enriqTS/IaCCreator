"""Route table configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class RouteTableConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.ROUTE_TABLE] = ServiceType.ROUTE_TABLE
    vpc_id: str = TerraformField("", description="VPC ID")
    destination_cidr_block: str = TerraformField(
        "0.0.0.0/0", group="Route", description="Route destination"
    )
    gateway_id: str = TerraformField(
        "", group="Route", description="Internet or virtual private gateway ID"
    )
