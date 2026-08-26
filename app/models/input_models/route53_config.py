"""Route 53 hosted zone configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, VisibleWhen


class Route53Config(BaseServiceConfig):
    service_type: Literal[ServiceType.ROUTE53] = ServiceType.ROUTE53
    zone_name: str = TerraformField("example.com", description="DNS zone name")
    comment: str | None = TerraformField(None, description="Hosted zone comment")
    private_zone: bool = TerraformField(
        False, description="Create a private hosted zone"
    )
    vpc_id: str | None = TerraformField(
        None,
        description="VPC ID for a private hosted zone",
        visible_when=VisibleWhen(field="private_zone", equals=True),
    )
    vpc_region: str | None = TerraformField(
        None,
        description="VPC region for a private hosted zone",
        visible_when=VisibleWhen(field="private_zone", equals=True),
    )
