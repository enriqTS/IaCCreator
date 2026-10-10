from pydantic import StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class OrganizationDelegationConfig(BaseConnectionConfig):
    account_id: StrictStr = ConnectionField(
        ...,
        label="Delegated member account ID",
        description="Existing active member account; Terraform runs in the management account",
        validation=ValidationRule(pattern=r"^[0-9]{12}$"),
    )

    @field_validator("account_id")
    @classmethod
    def nonzero_account(cls, value: str) -> str:
        if value == "000000000000":
            raise ValueError("A delegated member needs a nonzero AWS account ID")
        return value
