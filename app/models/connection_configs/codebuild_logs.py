"""Build logs use a bounded literal stream prefix within the managed group."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

STREAM_PREFIX_PATTERN = r"^[A-Za-z0-9_./#-]{1,128}$"
KMS_KEY_ARN_PATTERN = r"^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/[A-Za-z0-9-]+$"


class CodeBuildLogsConfig(BaseConnectionConfig):
    stream_prefix: str = ConnectionField(
        "build",
        label="Log stream prefix",
        validation=ValidationRule(pattern=STREAM_PREFIX_PATTERN),
    )
