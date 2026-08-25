"""Typed commands for backend-owned linked connection entries."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.diagram_models import DiagramStateInput


class CreateLinkedEntry(BaseModel):
    """Create a schema-defined linked entry for a connector."""

    operation: Literal["create"]
    connector_id: str
    field_key: str
    display_value: str
    entry_values: dict[str, Any] = Field(default_factory=dict)


class UpdateLinkedEntry(BaseModel):
    """Update one editable field on a schema-defined linked entry."""

    operation: Literal["update"]
    connector_id: str
    field_key: str
    display_value: str
    entry_field_key: str
    entry_field_value: Any


class RemoveLinkedEntry(BaseModel):
    """Remove a schema-defined linked entry for a connector."""

    operation: Literal["remove"]
    connector_id: str | None = None
    source_block_id: str | None = None
    field_key: str
    display_value: str


LinkedEntryOperation = CreateLinkedEntry | UpdateLinkedEntry | RemoveLinkedEntry


class ApplyConnectionOperationRequest(BaseModel):
    """Canonical diagram plus a linked-entry editing intent."""

    diagram: DiagramStateInput
    operation: LinkedEntryOperation = Field(discriminator="operation")
