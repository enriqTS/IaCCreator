"""Route selection and scopes for a Cognito HTTP API JWT authorizer."""

import re

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule
from app.models.input_models.api_gateway_route import HTTP_METHODS


class CognitoApiGatewayConfig(BaseConnectionConfig):
    path: str = ConnectionField(
        ...,
        label="Route path",
        description="Path of an existing HTTP API route",
        validation=ValidationRule(pattern=r"^/[A-Za-z0-9_./{}+\-]*$"),
    )
    method: str = ConnectionField(
        "ANY",
        label="Method",
        type="select",
        options=[OptionEntry(value=value, label=value) for value in HTTP_METHODS],
        validation=ValidationRule(allowed_values=list(HTTP_METHODS)),
    )
    authorization_scopes: str | None = ConnectionField(
        None,
        label="Authorization scopes",
        description="Comma-separated scopes; omit to inherit route settings, or use an empty value to allow tokens without scopes",
        placeholder="Optional comma-separated scopes",
    )

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value):
        return value.upper() if isinstance(value, str) else value

    @field_validator("authorization_scopes")
    @classmethod
    def normalize_scopes(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return value if value is None else ""
        scopes = [scope.strip() for scope in value.split(",")]
        if any(
            not re.fullmatch(r"[!\x23-\x2b\x2d-\x5b\x5d-\x7e]+", scope)
            for scope in scopes
        ):
            raise ValueError(
                "Authorization scopes must be nonempty ASCII OAuth scope names separated by commas"
            )
        return ",".join(sorted(set(scopes)))
