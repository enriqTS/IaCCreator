from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class TransitGatewayConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.TRANSIT_GATEWAY] = ServiceType.TRANSIT_GATEWAY
    description: str = TerraformField(
        "Managed transit gateway", description="Transit gateway description"
    )
    amazon_side_asn: int = TerraformField(
        64512, description="Private ASN for the Amazon side"
    )
    dns_support: bool = TerraformField(True, description="Enable DNS support")
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Transit gateway tags"
    )
