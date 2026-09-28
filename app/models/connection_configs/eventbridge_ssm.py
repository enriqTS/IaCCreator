"""Configuration for EventBridge Run Command document targets."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EventBridgeSsmConfig(BaseConnectionConfig):
    instance_id: str = ConnectionField(
        ...,
        label="EC2 Instance ID",
        description="Managed EC2 instance that receives the command",
        placeholder="i-0123456789abcdef0",
        validation=ValidationRule(pattern=r"^i-(?:[0-9a-f]{8}|[0-9a-f]{17})$"),
    )
    target_id: str | None = ConnectionField(
        None,
        label="Target Id",
        description="Identifier for this target within the rule",
        validation=ValidationRule(pattern=r"^[\w.\-]{1,64}$"),
    )
