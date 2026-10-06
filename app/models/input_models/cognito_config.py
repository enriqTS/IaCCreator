"""Amazon Cognito user pool configuration model."""

from typing import Literal

from pydantic import field_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class CognitoConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.COGNITO] = ServiceType.COGNITO
    username_attributes: str = TerraformField(
        "email",
        description="Attribute used as the username",
        options=[
            OptionEntry(value="email", label="Email"),
            OptionEntry(value="phone_number", label="Phone number"),
        ],
    )
    auto_verified_attributes: bool = TerraformField(
        True, description="Automatically verify the username attribute"
    )
    mfa_configuration: str = TerraformField(
        "OFF",
        description="Multi-factor authentication mode",
        options=[
            OptionEntry(value=value, label=value.title())
            for value in ("OFF", "ON", "OPTIONAL")
        ],
    )
    create_client: bool = TerraformField(
        True, description="Create an application client"
    )
    domain_prefix: str | None = TerraformField(
        None,
        description="Optional hosted sign-in domain prefix; unique within the AWS Region",
        validation=ValidationRule(pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"),
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    )

    @field_validator("domain_prefix")
    @classmethod
    def validate_domain_prefix(cls, value: str | None) -> str | None:
        if value and any(
            reserved in value for reserved in ("aws", "amazon", "cognito")
        ):
            raise ValueError(
                "Cognito domain prefixes cannot contain aws, amazon, or cognito"
            )
        return value
