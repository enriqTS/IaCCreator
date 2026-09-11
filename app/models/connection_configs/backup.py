"""Typed backup selection configuration."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class BackupSelectionConfig(BaseConnectionConfig):
    role_arn: str = ConnectionField(
        ...,
        label="Backup service role ARN",
        description="External role trusted by backup.amazonaws.com with backup and KMS permissions for this resource",
        validation=ValidationRule(
            pattern=r"^arn:aws(?:-[a-z]+)*:iam::[0-9]{12}:role/[A-Za-z0-9_+=,.@/-]+$"
        ),
    )
