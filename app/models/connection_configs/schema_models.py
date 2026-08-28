"""Response models for the connection catalog endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.models.connection_configs._metadata import ConnectionFieldSchema


class ConnectionSchemaEntry(BaseModel):
    """One connection kind, as offered to the diagram editor."""

    source: str
    target: str
    connection_type: str
    label: str
    is_default: bool
    region_policy: Literal["same-region", "cross-region"]
    fields: list[ConnectionFieldSchema]


class ConnectionSchemasResponse(BaseModel):
    """Every connection kind the backend can generate."""

    connections: list[ConnectionSchemaEntry]
