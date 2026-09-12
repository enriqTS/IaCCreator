"""Typed S3 live-replication rules."""

from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.storage import S3LocationConfig
from app.models.input_models._metadata import ValidationRule


class S3ReplicationConfig(S3LocationConfig):
    role_arn: str = ConnectionField(
        ...,
        label="Replication role ARN",
        description="External S3-trusted role with source, destination, and KMS permissions",
        validation=ValidationRule(
            pattern=r"^arn:aws(?:-[a-z]+)*:iam::[0-9]{12}:role/[A-Za-z0-9_+=,.@/-]+$"
        ),
    )
    replica_kms_key_arn: str | None = ConnectionField(
        None,
        label="External replica KMS key ARN",
        description="Used when the destination has no managed KMS connection",
        validation=ValidationRule(
            pattern=r"^arn:aws(?:-[a-z]+)*:kms:[a-z0-9-]+:[0-9]{12}:(?:key|alias)/[A-Za-z0-9_/-]+$"
        ),
    )
