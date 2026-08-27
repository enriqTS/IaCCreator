from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ClientVpnConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.CLIENT_VPN] = ServiceType.CLIENT_VPN
    description: str = TerraformField(
        "Managed client VPN", description="Client VPN endpoint description"
    )
    client_cidr_block: str = TerraformField(
        "10.100.0.0/22", description="Client IPv4 address pool"
    )
    server_certificate_arn: str = TerraformField(
        "", description="ACM server certificate ARN"
    )
    root_certificate_chain_arn: str = TerraformField(
        "", description="ACM client root certificate chain ARN"
    )
    split_tunnel: bool = TerraformField(True, description="Enable split-tunnel routing")
    transport_protocol: str = TerraformField(
        "udp", description="VPN transport protocol"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Client VPN tags"
    )
