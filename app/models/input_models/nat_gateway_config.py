"""NAT gateway configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField, VisibleWhen


class NatGatewayConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.NAT_GATEWAY] = ServiceType.NAT_GATEWAY
    subnet_id: str = TerraformField("", description="Subnet ID")
    connectivity_type: str = TerraformField(
        "public",
        description="Connectivity type",
        options=[
            OptionEntry(value="public", label="Public"),
            OptionEntry(value="private", label="Private"),
        ],
    )
    allocation_id: str | None = TerraformField(
        None,
        description="Elastic IP allocation ID for a public gateway",
        visible_when=VisibleWhen(field="connectivity_type", equals="public"),
    )
