"""Typed storage connection settings."""

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule


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


class EbsAttachmentConfig(BaseConnectionConfig):
    """An additional Linux block device attached to an EC2 instance."""

    device_name: str = ConnectionField(
        "/dev/sdf",
        label="Device name",
        description="EC2 attachment device name; formatting and mounting remain OS tasks",
        validation=ValidationRule(pattern=r"^/dev/(sd|xvd)[f-p]$"),
    )


class EfsLambdaMountConfig(BaseConnectionConfig):
    """A non-root EFS access point mounted into Lambda."""

    local_mount_path: str = ConnectionField(
        "/mnt/efs",
        label="Lambda mount path",
        validation=ValidationRule(pattern=r"^/mnt/[A-Za-z0-9_-]+$"),
    )
    root_directory: str | None = ConnectionField(
        None,
        label="EFS directory",
        description="Defaults to a directory named after the Lambda function",
        validation=ValidationRule(pattern=r"^/[A-Za-z0-9_-]+$"),
    )
    uid: int = ConnectionField(
        1000,
        label="POSIX user ID",
        type="number",
        validation=ValidationRule(min=1, max=4294967294),
    )
    gid: int = ConnectionField(
        1000,
        label="POSIX group ID",
        type="number",
        validation=ValidationRule(min=1, max=4294967294),
    )
    access: str = ConnectionField(
        "read",
        label="Access",
        type="select",
        options=[
            OptionEntry(value="read", label="Read only"),
            OptionEntry(value="write", label="Read and write"),
        ],
        validation=ValidationRule(allowed_values=["read", "write"]),
    )
