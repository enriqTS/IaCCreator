"""Configuration for standard CodeBuild targets on EventBridge rules."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EventBridgeCodeBuildConfig(BaseConnectionConfig):
    target_id: str | None = ConnectionField(
        None,
        label="Target Id",
        description="Identifier for this target within the rule",
        validation=ValidationRule(pattern=r"^[\w.\-]{1,64}$"),
    )
