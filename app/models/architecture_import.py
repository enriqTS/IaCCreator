"""Typed contracts for importing generation architectures into the editor."""

from pydantic import BaseModel

from app.models.diagram_models import DiagramStateInput
from app.models.input_models import ArchitectureDescription


class ArchitectureImportRequest(BaseModel):
    architecture: ArchitectureDescription


class ArchitectureImportResponse(BaseModel):
    diagram: DiagramStateInput
    imported_resource_count: int
    inferred_container_count: int
