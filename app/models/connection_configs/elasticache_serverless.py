"""Select an external IAM-enabled cache user without reading credentials."""

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class ServerlessCacheIamConfig(BaseConnectionConfig):
    user_id: str = ConnectionField(
        ...,
        label="Existing IAM cache user ID",
        description="IAM-enabled user whose user name equals its ID and which belongs to the cache user group",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9-]{0,39}$"),
    )

    @field_validator("user_id")
    @classmethod
    def normalize_user(cls, value: str) -> str:
        return value.lower()
