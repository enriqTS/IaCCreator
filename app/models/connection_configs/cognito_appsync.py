"""Cognito user-pool authentication options for an AppSync API."""

from typing import Literal

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, VisibleWhen


class CognitoAppSyncConfig(BaseConnectionConfig):
    mode: Literal["default", "additional"] = ConnectionField(
        "default",
        label="Authentication mode",
        type="select",
        options=[
            OptionEntry(value="default", label="Default authentication"),
            OptionEntry(value="additional", label="Additional authentication"),
        ],
    )
    restrict_to_client: bool = ConnectionField(
        True,
        label="Restrict to generated client",
        type="boolean",
        description="Accept tokens only from this Cognito node's generated application client",
    )
    default_action: Literal["ALLOW", "DENY"] = ConnectionField(
        "ALLOW",
        label="Default field access",
        type="select",
        options=[
            OptionEntry(value="ALLOW", label="Allow authenticated users"),
            OptionEntry(value="DENY", label="Require explicit group directives"),
        ],
        visible_when=VisibleWhen(field="mode", equals="default"),
    )

    @model_validator(mode="after")
    def validate_action(self):
        if self.mode == "additional" and self.default_action != "ALLOW":
            raise ValueError(
                "Default field access applies only to default authentication"
            )
        return self
