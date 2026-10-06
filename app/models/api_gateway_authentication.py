"""Connection-derived JWT authorization for an HTTP API route."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CognitoJwtRouteBinding:
    pool_name: str
    scopes: tuple[str, ...]

    @property
    def authorizer_resource(self) -> str:
        return f"cognito_{self.pool_name}_jwt"
