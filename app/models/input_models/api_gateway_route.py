"""Typed route entry for API Gateway, shared by the generator and the connection schema."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

HTTP_METHODS: tuple[str, ...] = (
    "ANY",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
)


class ApiGatewayRoute(BaseModel):
    """One route on an API Gateway, as stored in the gateway's own config."""

    # model_selection_expression is an AWS field name, not a Pydantic namespace clash
    model_config = ConfigDict(protected_namespaces=())

    # HTTP APIs address a route by path; WebSocket APIs use route_key
    path: str | None = None
    route_key: str | None = None
    methods: list[str] = Field(default_factory=lambda: ["ANY"])
    # Bind the route to the resource handling it; the id survives renames
    integration_name: str | None = None
    integration_id: str | None = None
    integration_type: str | None = None
    payload_format_version: str | None = None
    authorizer_name: str | None = None
    api_key_required: bool = False
    route_response_key: str | None = None
    authorization_type: str | None = None
    authorization_scopes: list[str] | None = None
    operation_name: str | None = None
    model_selection_expression: str | None = None
    route_response_selection_expression: str | None = None

    @field_validator("methods")
    @classmethod
    def _normalise_methods(cls, value: list[str]) -> list[str]:
        """Uppercase methods and reject anything API Gateway cannot route."""
        normalised = [m.upper() for m in value]
        invalid = [m for m in normalised if m not in HTTP_METHODS]
        if invalid:
            raise ValueError(
                f"invalid HTTP method(s) {', '.join(invalid)}; "
                f"expected one of {', '.join(HTTP_METHODS)}"
            )
        return normalised

    def as_dict(self) -> dict:
        """Render as a plain dict, dropping unset keys so lookups keep their fallbacks."""
        return self.model_dump(exclude_none=True)


def route_dicts(routes: list["ApiGatewayRoute"] | None) -> list[dict] | None:
    """Convert a typed route list into the dict form the generator reads."""
    if routes is None:
        return None
    return [r.as_dict() for r in routes]
