from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class SiteToSiteVpnConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.SITE_TO_SITE_VPN] = ServiceType.SITE_TO_SITE_VPN
    customer_gateway_id: str = TerraformField("", description="Customer gateway ID")
    transit_gateway_id: str = TerraformField("", description="Transit gateway ID")
    static_routes_only: bool = TerraformField(
        False, description="Use static routes instead of BGP"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="VPN connection tags"
    )
