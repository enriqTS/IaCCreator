"""Semantic containment operation API contracts."""

from pydantic import BaseModel

from app.models.containment import ContainmentOperation, ContainmentResolution
from app.models.diagram_models import DiagramStateInput


class ApplyContainmentOperationRequest(BaseModel):
    diagram: DiagramStateInput
    operation: ContainmentOperation


class ApplyContainmentOperationResponse(BaseModel):
    diagram: DiagramStateInput
    resolution: ContainmentResolution
