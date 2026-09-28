"""Route selection for EventBridge API Gateway targets."""

import re

from pydantic import field_validator

from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.eventbridge_invocation import (
    EventBridgeInvocationConfig,
)
from app.models.input_models._metadata import OptionEntry, ValidationRule


class EventBridgeApiGatewayConfig(EventBridgeInvocationConfig):
    stage: str = ConnectionField(
        "$default",
        label="Stage",
        description="Deployed HTTP API stage to invoke",
    )
    method: str = ConnectionField(
        "POST",
        label="Method",
        type="select",
        options=[OptionEntry(value="POST", label="POST")],
        validation=ValidationRule(allowed_values=["POST"]),
    )
    path: str = ConnectionField(
        ...,
        label="Route path",
        description="Static path of an existing IAM-authorized POST route",
    )

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, value: str) -> str:
        if not re.fullmatch(r"\$default|[A-Za-z0-9_-]{1,128}", value):
            raise ValueError("Stage must be $default or a valid API Gateway stage name")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if not re.fullmatch(r"/(?:[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*)?", value):
            raise ValueError("Route path must be static and start with /")
        return value
