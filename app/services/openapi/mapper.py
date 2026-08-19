"""Maps an OpenAPI document onto API Gateway configuration."""

from __future__ import annotations

import uuid
from typing import Any

from app.services.openapi.models import (
    ImportedAuthorizer,
    ImportedRoute,
    ImportedSettings,
    ImportSummary,
    OpenApiDocument,
    OpenApiImportResponse,
)

HTTP_METHODS = ("get", "post", "put", "delete", "patch", "head", "options")

_JWT_SCHEME_TYPES = ("oauth2", "openIdConnect")


def _is_api_key_scheme(scheme: dict[str, Any]) -> bool:
    """An apiKey scheme passed in the X-API-Key header."""
    return (
        scheme.get("type") == "apiKey"
        and scheme.get("in") == "header"
        and str(scheme.get("name", "")).lower() == "x-api-key"
    )


def _issuer_url(scheme: dict[str, Any]) -> str | None:
    """Issuer URL for a JWT-style scheme."""
    if scheme.get("type") == "openIdConnect":
        return scheme.get("openIdConnectUrl")
    if scheme.get("type") == "oauth2":
        flows = scheme.get("flows") or {}
        for flow in ("authorizationCode", "clientCredentials", "password", "implicit"):
            token_url = (flows.get(flow) or {}).get("tokenUrl")
            if token_url:
                return token_url
    return None


def _apply_security(
    route: ImportedRoute,
    operation: dict[str, Any],
    global_security: list[dict[str, Any]],
    schemes: dict[str, Any],
) -> None:
    """Apply operation-level security, falling back to the document's global security."""
    operation_security = operation.get("security")
    effective = (
        operation_security if operation_security is not None else global_security
    )

    # An explicitly empty list means the operation opts out of auth
    if operation_security is not None and not operation_security:
        route.api_key_required = False
        route.authorizer_name = None
        return

    for requirement in effective:
        for scheme_name in requirement:
            scheme = schemes.get(scheme_name)
            if not scheme:
                continue
            if _is_api_key_scheme(scheme):
                route.api_key_required = True
            if scheme.get("type") in _JWT_SCHEME_TYPES:
                route.authorizer_name = scheme_name


def _detect_cors(paths: dict[str, Any]) -> dict[str, str] | None:
    """Read CORS headers off any OPTIONS response that declares an allow-origin header."""
    for path_item in paths.values():
        options = (path_item or {}).get("options")
        if not options:
            continue
        for response in (options.get("responses") or {}).values():
            headers = (response or {}).get("headers") or {}
            cors = {
                name: str((definition or {}).get("schema", {}).get("default", ""))
                for name, definition in headers.items()
                if name.lower().startswith("access-control-")
            }
            if any(name.lower() == "access-control-allow-origin" for name in cors):
                return cors
    return None


def map_openapi(
    document: OpenApiDocument, selected_server_url: str | None = None
) -> OpenApiImportResponse:
    """Derive routes, authorizers and settings from an OpenAPI document."""
    schemes: dict[str, Any] = (document.components or {}).get(
        "securitySchemes", {}
    ) or {}
    global_security = document.security or []

    authorizers = [
        ImportedAuthorizer(
            id=str(uuid.uuid4()),
            name=name,
            issuer_url=_issuer_url(scheme),
        )
        for name, scheme in schemes.items()
        if scheme.get("type") in _JWT_SCHEME_TYPES
    ]

    global_api_key = any(
        _is_api_key_scheme(schemes[name])
        for requirement in global_security
        for name in requirement
        if name in schemes
    )

    routes: list[ImportedRoute] = []
    for path, path_item in document.paths.items():
        if not path_item:
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not operation:
                continue
            route = ImportedRoute(
                id=str(uuid.uuid4()),
                methods=[method.upper()],
                path=path,
                target_service_uri=(
                    selected_server_url + path if selected_server_url else None
                ),
                tag=(operation.get("tags") or [None])[0],
            )
            _apply_security(route, operation, global_security, schemes)
            routes.append(route)

    cors = _detect_cors(document.paths)

    return OpenApiImportResponse(
        routes=routes,
        authorizers=authorizers,
        settings=ImportedSettings(
            api_name=document.info.get("title") or None,
            description=document.info.get("description") or None,
            api_key_required=global_api_key or None,
            cors_configuration=cors,
        ),
        server_urls=[s.get("url", "") for s in document.servers if s.get("url")],
        summary=ImportSummary(
            route_count=len(routes),
            authorizer_count=len(authorizers),
            has_api_key=global_api_key or any(r.api_key_required for r in routes),
            has_cors=cors is not None,
        ),
    )
