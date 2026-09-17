"""Typed DMS endpoint identity and authentication settings."""

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.database import DatabaseIamAuthConfig
from app.models.input_models._metadata import ValidationRule


class DmsEndpointConfig(BaseConnectionConfig):
    endpoint_id: str = ConnectionField(
        ...,
        label="Endpoint identifier",
        description="Unique DMS endpoint identifier within this project",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9-]{0,254}$"),
    )
    database_name: str = ConnectionField(
        ...,
        label="Database name",
        description="Existing database used by this migration endpoint",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$"),
    )
    certificate_arn: str = ConnectionField(
        ...,
        label="Imported DMS CA certificate ARN",
        description="DMS-imported database CA certificate in the replication instance's account and Region",
        validation=ValidationRule(
            pattern=r"^arn:aws(?:-[a-z-]+)?:dms:[a-z0-9-]+:[0-9]{12}:cert:[A-Za-z0-9_-]+$"
        ),
    )

    @field_validator("endpoint_id")
    @classmethod
    def normalize_endpoint_id(cls, value: str) -> str:
        if "--" in value or value.endswith("-"):
            raise ValueError(
                "Endpoint identifiers cannot contain consecutive or trailing hyphens"
            )
        return value.lower()


class DmsIamEndpointConfig(DmsEndpointConfig, DatabaseIamAuthConfig):
    pass


class DmsSecretEndpointConfig(DmsEndpointConfig):
    secrets_manager_arn: str = ConnectionField(
        ...,
        label="Database secret ARN",
        description="Existing secret containing host, port, username and password for the selected database",
        validation=ValidationRule(
            pattern=r"^arn:aws(?:-[a-z-]+)?:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:[A-Za-z0-9/_+=.@-]+-[A-Za-z0-9]{6}$"
        ),
    )
    secrets_manager_access_role_arn: str = ConnectionField(
        ...,
        label="DMS secret access role ARN",
        description="Existing DMS-trusted role with access to the secret and its encryption key",
        validation=ValidationRule(
            pattern=r"^arn:aws(?:-[a-z-]+)?:iam::[0-9]{12}:role/[A-Za-z0-9/+=,.@_-]+$"
        ),
    )
