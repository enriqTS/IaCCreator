"""Select an externally managed IAM-authenticated MemoryDB user."""

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class MemoryDbIamConfig(BaseConnectionConfig):
    user_name: str = ConnectionField(
        ...,
        label="Existing IAM user name",
        description="MemoryDB user with IAM authentication and membership in the cluster ACL",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9-]*$"),
    )

    @field_validator("user_name")
    @classmethod
    def lowercase_user(cls, value: str) -> str:
        return value.lower()
