"""Request and response models for OpenAPI import."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OpenApiImportRequest(BaseModel):
    """Raw OpenAPI document text, JSON or YAML."""

    content: str
    selected_server_url: str | None = None


class ImportedRoute(BaseModel):
    """A route derived from one path/method pair."""

    id: str
    methods: list[str]
    path: str
    integration_ref: str = ""
    integration_type: str = "HTTP_PROXY"
    target_service_uri: str | None = None
    tag: str | None = None
    api_key_required: bool | None = None
    authorizer_name: str | None = None


class ImportedAuthorizer(BaseModel):
    """A JWT authorizer derived from an oauth2 or openIdConnect scheme."""

    id: str
    name: str
    type: str = "JWT"
    issuer_url: str | None = None
    audience: list[str] = Field(default_factory=list)


class ImportedSettings(BaseModel):
    """Gateway-level settings derived from the document."""

    api_name: str | None = None
    description: str | None = None
    api_key_required: bool | None = None
    cors_configuration: dict[str, str] | None = None
    protocol_type: str = "HTTP"


class ImportSummary(BaseModel):
    """What the import found, for the confirmation screen."""

    route_count: int
    authorizer_count: int
    has_api_key: bool
    has_cors: bool
    protocol_type: str = "HTTP"


class OpenApiImportResponse(BaseModel):
    """Everything the editor needs to populate an API Gateway block."""

    routes: list[ImportedRoute]
    authorizers: list[ImportedAuthorizer]
    settings: ImportedSettings
    server_urls: list[str]
    summary: ImportSummary


class OpenApiDocument(BaseModel):
    """Loosely typed view of the parts of an OpenAPI document we read."""

    model_config = {"extra": "allow"}

    openapi: str
    info: dict[str, Any]
    paths: dict[str, Any]
    servers: list[dict[str, Any]] = Field(default_factory=list)
    security: list[dict[str, Any]] = Field(default_factory=list)
    components: dict[str, Any] = Field(default_factory=dict)
