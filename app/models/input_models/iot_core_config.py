from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class IotCoreConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.IOT_CORE] = ServiceType.IOT_CORE
    thing_name: str = TerraformField("connected-device", description="IoT thing name")
    thing_type_name: str = TerraformField("", description="Optional IoT thing type")
    attributes: dict[str, str] = TerraformField(
        default_factory=dict, description="Thing registry attributes"
    )
