from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class GlobalAcceleratorConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.GLOBAL_ACCELERATOR] = (
        ServiceType.GLOBAL_ACCELERATOR
    )
    accelerator_name: str = TerraformField(
        "global-entrypoint", description="Accelerator name"
    )
    enabled: bool = TerraformField(True, description="Enable the accelerator")
    ip_address_type: str = TerraformField(
        "IPV4", description="Accelerator IP address type"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Accelerator tags"
    )
