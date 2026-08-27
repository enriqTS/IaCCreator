from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class IvsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.INTERACTIVE_VIDEO_SERVICE] = (
        ServiceType.INTERACTIVE_VIDEO_SERVICE
    )
    channel_name: str = TerraformField("live-channel", description="IVS channel name")
    channel_type: str = TerraformField(
        "STANDARD",
        description="IVS channel type",
        options=[
            OptionEntry(value="STANDARD", label="Standard"),
            OptionEntry(value="BASIC", label="Basic"),
            OptionEntry(value="ADVANCED_SD", label="Advanced SD"),
            OptionEntry(value="ADVANCED_HD", label="Advanced HD"),
        ],
    )
    latency_mode: str = TerraformField(
        "LOW",
        description="Channel latency mode",
        options=[
            OptionEntry(value="LOW", label="Low latency"),
            OptionEntry(value="NORMAL", label="Normal latency"),
        ],
    )
    authorized: bool = TerraformField(
        False, description="Require playback authorization"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Channel tags"
    )
