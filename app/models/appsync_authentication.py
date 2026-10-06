"""Connection-derived Cognito authentication bindings for an AppSync API."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CognitoUserPoolBinding:
    mode: Literal["default", "additional"]
    user_pool_id_input: str
    region_input: str
    client_id_input: str | None
    default_action: Literal["ALLOW", "DENY"]
