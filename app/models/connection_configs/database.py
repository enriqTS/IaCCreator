"""Database users must be explicitly selected for IAM authentication."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class DatabaseIamAuthConfig(BaseConnectionConfig):
    database_user: str = ConnectionField(
        ...,
        label="Database user",
        description="Existing IAM-enabled database user; SQL privileges are managed separately",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,31}$"),
    )
