"""DMS IAM endpoints select an existing database user and imported CA certificate."""

from pydantic import field_validator

from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.database import DatabaseIamAuthConfig
from app.models.input_models._metadata import ValidationRule


class DmsIamEndpointConfig(DatabaseIamAuthConfig):
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
