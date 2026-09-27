"""EventBridge invocation targets accept bounded, valid constant JSON."""

import json

from pydantic import field_validator

from app.models.connection_configs.configs import EventBridgeTargetConfig


class EventBridgeInvocationConfig(EventBridgeTargetConfig):
    @field_validator("input")
    @classmethod
    def validate_input(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if len(value.encode("utf-8")) > 8192:
            raise ValueError("Constant input must not exceed 8192 bytes")

        def reject_constant(value):
            raise ValueError("Constant input must be valid JSON")

        try:
            json.loads(value, parse_constant=reject_constant)
        except (ValueError, RecursionError) as exc:
            raise ValueError("Constant input must be valid JSON") from exc
        return value
