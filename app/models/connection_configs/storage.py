"""Typed storage connection settings."""

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry


class S3NotificationConfig(BaseConnectionConfig):
    """Object notifications for a managed S3 destination."""

    events: list[str] = ConnectionField(
        ["s3:ObjectCreated:*"],
        label="Events",
        description="Object events delivered to the destination",
        type="multiSelect",
        options=[
            OptionEntry(value="s3:ObjectCreated:*", label="Object created"),
            OptionEntry(value="s3:ObjectRemoved:*", label="Object removed"),
            OptionEntry(value="s3:ObjectRestore:*", label="Object restored"),
        ],
    )
    filter_prefix: str | None = ConnectionField(
        None,
        label="Key Prefix",
        description="Only notify for keys starting with this prefix",
        placeholder="Optional, e.g. uploads/",
    )
    filter_suffix: str | None = ConnectionField(
        None,
        label="Key Suffix",
        description="Only notify for keys ending with this suffix",
        placeholder="Optional, e.g. .jpg",
    )

    @field_validator("events")
    @classmethod
    def validate_events(cls, value: list[str]) -> list[str]:
        allowed = {"s3:ObjectCreated:*", "s3:ObjectRemoved:*", "s3:ObjectRestore:*"}
        if not value or any(event not in allowed for event in value):
            raise ValueError("Choose at least one supported S3 event type")
        return sorted(set(value))
