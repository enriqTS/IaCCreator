from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class NetworkFirewallConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.NETWORK_FIREWALL] = ServiceType.NETWORK_FIREWALL
    firewall_name: str = TerraformField("network-firewall", description="Firewall name")
    vpc_id: str = TerraformField("", description="VPC ID containing the firewall")
    subnet_ids: list[str] = TerraformField(
        [], description="Firewall endpoint subnet IDs"
    )
    firewall_policy_arn: str = TerraformField(
        "", description="Network Firewall policy ARN"
    )
    delete_protection: bool = TerraformField(
        False, description="Protect the firewall from deletion"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Firewall tags"
    )
