"""Amazon WorkSpaces workspace configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
    VisibleWhen,
)


class WorkSpacesConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.WORKSPACES] = ServiceType.WORKSPACES
    directory_id: str = TerraformField(
        "", description="AWS Directory Service directory ID"
    )
    bundle_id: str = TerraformField("", description="WorkSpaces bundle ID")
    user_name: str = TerraformField("", description="Directory user name")
    running_mode: str = TerraformField(
        "AUTO_STOP",
        description="Workspace running mode",
        options=[
            OptionEntry(value="AUTO_STOP", label="Auto stop"),
            OptionEntry(value="ALWAYS_ON", label="Always on"),
        ],
    )
    running_mode_auto_stop_timeout_in_minutes: int = TerraformField(
        60,
        title="Auto-stop timeout",
        description="Idle time before an auto-stop workspace stops",
        validation=ValidationRule(min=60, max=600),
        visible_when=VisibleWhen(field="running_mode", equals="AUTO_STOP"),
    )
    root_volume_encryption_enabled: bool = TerraformField(
        True, description="Encrypt the root volume"
    )
    user_volume_encryption_enabled: bool = TerraformField(
        True, description="Encrypt the user volume"
    )
    volume_encryption_key: str | None = TerraformField(
        None, description="KMS key ARN or alias"
    )
