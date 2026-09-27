"""Kinesis event targets select a single event field as the partition key."""

from pydantic import field_validator

from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.eventbridge_invocation import (
    EventBridgeInvocationConfig,
)
from app.models.input_models._metadata import ValidationRule


class EventBridgeKinesisConfig(EventBridgeInvocationConfig):
    partition_key_path: str | None = ConnectionField(
        None,
        label="Partition key path (optional)",
        description="Dot-notation event field, up to 256 characters; omit to use the event ID",
        placeholder="$.detail.customerId",
        validation=ValidationRule(pattern=r"^\$(?:\.[A-Za-z_][A-Za-z0-9_-]*)+$"),
    )

    @field_validator("partition_key_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return None if value == "" else value

    @field_validator("partition_key_path")
    @classmethod
    def validate_path_length(cls, value):
        if value is not None and len(value) > 256:
            raise ValueError("Partition key paths must not exceed 256 characters")
        return value
