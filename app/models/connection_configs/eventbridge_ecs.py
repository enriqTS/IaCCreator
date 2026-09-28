"""Configuration for running ECS tasks from EventBridge rules."""

from pydantic import StrictInt

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EventBridgeEcsConfig(BaseConnectionConfig):
    target_id: str | None = ConnectionField(
        None,
        label="Target Id",
        description="Identifier for this target within the rule",
        validation=ValidationRule(pattern=r"^[\w.\-]{1,64}$"),
    )
    task_count: StrictInt = ConnectionField(
        1,
        label="Task count",
        type="number",
        description="Number of Fargate tasks started for each matching event",
        validation=ValidationRule(min=1, max=10),
    )
