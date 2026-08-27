from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class IotDeviceManagementConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.IOT_DEVICE_MANAGEMENT] = (
        ServiceType.IOT_DEVICE_MANAGEMENT
    )
    thing_group_name: str = TerraformField(
        "managed-devices", description="IoT thing group name"
    )
    parent_group_name: str = TerraformField(
        "", description="Optional parent thing group name"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Thing group tags"
    )
