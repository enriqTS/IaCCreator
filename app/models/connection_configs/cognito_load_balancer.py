"""Browser authentication settings for an existing HTTPS listener."""

import re
from typing import Literal

from pydantic import StrictInt, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule


class CognitoLoadBalancerConfig(BaseConnectionConfig):
    listener_port: StrictInt = ConnectionField(
        443,
        label="HTTPS listener port",
        type="number",
        validation=ValidationRule(min=1, max=65535),
    )
    application_hostname: str = ConnectionField(
        ...,
        label="Application hostname",
        description="DNS hostname covered by the listener certificate and pointing to this ALB",
        placeholder="app.example.com",
    )
    scopes: str = ConnectionField(
        "openid",
        label="OAuth scopes",
        description="Space-separated built-in Cognito scopes, including openid",
    )
    on_unauthenticated_request: Literal["authenticate", "deny", "allow"] = (
        ConnectionField(
            "authenticate",
            label="Unauthenticated requests",
            type="select",
            options=[
                OptionEntry(value="authenticate", label="Redirect to sign in"),
                OptionEntry(value="deny", label="Deny"),
                OptionEntry(value="allow", label="Allow optional sign in"),
            ],
        )
    )
    session_timeout: StrictInt = ConnectionField(
        3600,
        label="Session timeout (seconds)",
        type="number",
        validation=ValidationRule(min=1, max=604800),
    )

    @field_validator("application_hostname", mode="before")
    @classmethod
    def normalize_hostname(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("application_hostname")
    @classmethod
    def validate_hostname(cls, value: str) -> str:
        labels = value.split(".")
        if (
            len(value) > 253
            or len(labels) < 2
            or labels[-1].isdigit()
            or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels
            )
        ):
            raise ValueError("Use a DNS hostname without a scheme, port, or path")
        return value

    @field_validator("scopes")
    @classmethod
    def normalize_scopes(cls, value: str) -> str:
        scopes = set(value.split())
        allowed = {
            "openid",
            "email",
            "profile",
            "phone",
            "aws.cognito.signin.user.admin",
        }
        if "openid" not in scopes or not scopes <= allowed:
            raise ValueError(
                "Include openid and use only built-in Cognito OAuth scopes"
            )
        return " ".join(sorted(scopes))
