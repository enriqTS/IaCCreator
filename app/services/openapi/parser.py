"""Parses raw OpenAPI text into a validated document."""

from __future__ import annotations

import json
from typing import Any

import yaml

from app.exceptions import DomainError
from app.services.openapi.models import OpenApiDocument


class OpenApiParseError(DomainError):
    """Raised when the supplied text is not a usable OpenAPI 3.x document."""


def _load(content: str) -> Any:
    """Load JSON, falling back to YAML."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise OpenApiParseError(
            "Invalid format: content is not valid JSON or YAML"
        ) from exc


def parse_openapi(content: str) -> OpenApiDocument:
    """Parse and structurally validate an OpenAPI 3.x document."""
    document = _load(content)
    if not isinstance(document, dict):
        raise OpenApiParseError("Invalid format: content is not valid JSON or YAML")

    version = document.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        raise OpenApiParseError(
            "Not a valid OpenAPI 3.x document: missing or unsupported 'openapi' version field"
        )
    if not isinstance(document.get("info"), dict):
        raise OpenApiParseError(
            "Not a valid OpenAPI 3.x document: missing 'info' object"
        )
    if not isinstance(document.get("paths"), dict):
        raise OpenApiParseError(
            "Not a valid OpenAPI 3.x document: missing 'paths' object"
        )

    return OpenApiDocument.model_validate(document)
