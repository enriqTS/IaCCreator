from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class DirectConnectConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.DIRECT_CONNECT] = ServiceType.DIRECT_CONNECT
    gateway_name: str = TerraformField(
        "direct-connect", description="Direct Connect gateway name"
    )
    amazon_side_asn: int = TerraformField(
        64512, description="Private ASN for the Amazon side"
    )
