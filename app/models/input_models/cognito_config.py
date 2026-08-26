"""Amazon Cognito user pool configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


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
