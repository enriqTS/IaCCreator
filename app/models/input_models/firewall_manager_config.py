from typing import Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class FirewallManagerConfig(BaseServiceConfig):
    _organization_delegation: bool = PrivateAttr(default=False)
    service_type: Literal[ServiceType.FIREWALL_MANAGER] = ServiceType.FIREWALL_MANAGER
    account_id: str = TerraformField(
        "", description="Firewall Manager administrator account ID"
    )
