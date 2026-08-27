from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class MediaLiveConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MEDIA_LIVE] = ServiceType.MEDIA_LIVE
    allowed_cidrs: list[str] = TerraformField(
        default_factory=lambda: ["0.0.0.0/0"],
        description="CIDR ranges allowed to push live video",
        min_length=1,
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Input security group tags"
    )
