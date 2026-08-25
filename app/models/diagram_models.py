"""Typed API contracts for the canonical editor diagram format."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.diagram_state import VISUAL_MODELS, DiagramState
from app.models.input_models import ServiceType
from app.persistence.models import DiagramSummary
from app.services.diagram_migrations import migrate_diagram_state


class DiagramStateInput(DiagramState):
    """Canonical diagram accepted by editor endpoints, with legacy migration."""

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy(cls, value: object) -> object:
        """Upgrade legacy API consumers before canonical validation."""
        required = {"version", "projectName", "environments", "connectors", "viewport"}
        if isinstance(value, dict) and not required.issubset(value):
            raise ValueError("Diagram is missing required fields")
        if isinstance(value, dict) and not isinstance(value.get("version"), int):
            raise ValueError("Diagram version must be an integer")
        if isinstance(value, dict) and value["version"] < 3:
            elements = value.get("elements")
            viewport = value.get("viewport")
            if not isinstance(elements, list) or not all(
                isinstance(element, dict) for element in elements
            ):
                raise ValueError("Legacy elements must be a list of objects")
            if not isinstance(viewport, dict) or not all(
                key in viewport for key in ("x", "y", "zoom")
            ):
                raise ValueError("Legacy viewport requires x, y and zoom")
            return migrate_diagram_state(value)
        return value

    @model_validator(mode="after")
    def validate_references(self) -> "DiagramStateInput":
        object_ids = {obj.id for obj in self.canvasObjects}
        if len(object_ids) != len(self.canvasObjects):
            raise ValueError("Canvas object IDs must be unique")
        group_ids = {group.id for group in self.objectGroups}
        if len(group_ids) != len(self.objectGroups):
            raise ValueError("Object group IDs must be unique")
        for obj in self.canvasObjects:
            if obj.objectType not in VISUAL_MODELS:
                raise ValueError(f"Unknown canvas object type: {obj.objectType}")
            if obj.objectType == "architecture-block":
                service_type = obj.model_extra.get("serviceType")
                try:
                    ServiceType(service_type)
                except ValueError as exc:
                    raise ValueError(f"Unknown service type: {service_type}") from exc
            if obj.objectType == "line":
                for key in ("sourceAnchorObjectId", "targetAnchorObjectId"):
                    target = obj.model_extra.get(key)
                    if target is not None and target not in object_ids:
                        raise ValueError(
                            f"Line {obj.id} references missing object {target}"
                        )
        connector_ids = {connector.id for connector in self.connectors}
        if len(connector_ids) != len(self.connectors):
            raise ValueError("Connector IDs must be unique")
        missing_connectors = [
            connector.id
            for connector in self.connectors
            if connector.sourceId not in object_ids
            or connector.targetId not in object_ids
        ]
        if missing_connectors:
            raise ValueError(
                f"Connectors reference missing objects: {missing_connectors}"
            )
        missing_groups = [
            obj.id
            for obj in self.canvasObjects
            if obj.groupId and obj.groupId not in group_ids
        ]
        if missing_groups:
            raise ValueError(f"Objects reference missing groups: {missing_groups}")
        missing_members = [
            member
            for group in self.objectGroups
            for member in group.memberIds
            if member not in object_ids
        ]
        if missing_members:
            raise ValueError(f"Groups reference missing objects: {missing_members}")
        return self


class DiagramIdResponse(BaseModel):
    """Identifier returned after a write."""

    id: str


class DiagramListResponse(BaseModel):
    """Session-scoped saved diagram summaries."""

    diagrams: list[DiagramSummary] = Field(default_factory=list)


class ResourceInitializationRequest(BaseModel):
    """Intent to place a service resource."""

    service_type: str
    existing_names: list[str] = Field(default_factory=list)


class ResourceInitializationResponse(BaseModel):
    """Backend-owned initial domain values for a resource."""

    name: str
    config: dict[str, Any]
    terraform_variables: dict[str, Any]
