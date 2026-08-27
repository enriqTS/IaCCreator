"""Typed API contracts for the canonical editor diagram format."""

from typing import Any

from pydantic import BaseModel, Field, TypeAdapter, model_validator

from app.models.diagram_state import VISUAL_MODELS, DiagramState
from app.models.input_models import ServiceType
from app.models.input_models._general import _get_cached_service_config_models
from app.persistence.models import DiagramSummary
from app.services.connection_handlers.registry import resolve_spec
from app.services.containment_catalog import (
    allowed_parent,
    is_container_capable,
    semantic_type,
)
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
        config_models = _get_cached_service_config_models()
        for obj in self.canvasObjects:
            if obj.objectType not in VISUAL_MODELS:
                raise ValueError(f"Unknown canvas object type: {obj.objectType}")
            if obj.objectType == "architecture-block":
                model = config_models.get(obj.serviceType)
                if model is not None:
                    unknown = set(obj.config) - set(model.model_fields)
                    if unknown:
                        raise ValueError(
                            f"Unknown {obj.serviceType.value} config fields: {sorted(unknown)}"
                        )
                    for name, value in obj.config.items():
                        adapter = TypeAdapter(model.model_fields[name].annotation)
                        validated = adapter.validate_python(value)
                        obj.config[name] = adapter.dump_python(validated, mode="json")
            if obj.objectType == "line":
                for key in ("sourceAnchorObjectId", "targetAnchorObjectId"):
                    target = getattr(obj, key)
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
        objects = {obj.id: obj for obj in self.canvasObjects}
        for connector in self.connectors:
            source = objects[connector.sourceId]
            target = objects[connector.targetId]
            if (
                source.objectType != "architecture-block"
                or target.objectType != "architecture-block"
            ):
                raise ValueError("Connectors must join architecture blocks")
            config = connector.connection_config or {}
            spec = resolve_spec(
                source.serviceType,
                target.serviceType,
                connector.connectionType,
                config,
            )
            if spec is None:
                spec = resolve_spec(
                    target.serviceType,
                    source.serviceType,
                    connector.connectionType,
                    config,
                )
                if spec is not None:
                    connector.sourceId, connector.targetId = (
                        connector.targetId,
                        connector.sourceId,
                    )
                    source, target = target, source
            if spec is None:
                raise ValueError(
                    f"Unsupported connection: {source.serviceType.value} to {target.serviceType.value}"
                )
            connector.connectionType = spec.connection_type
            editable = dict(config)
            editable.pop("connection_role", None)
            unknown = set(editable) - set(spec.config_model.model_fields)
            if unknown:
                raise ValueError(f"Unknown connection config fields: {sorted(unknown)}")
            for name, value in editable.items():
                adapter = TypeAdapter(spec.config_model.model_fields[name].annotation)
                validated = adapter.validate_python(value)
                config[name] = adapter.dump_python(validated, mode="json")
            connector.connection_config = config or None
        for obj in self.canvasObjects:
            parent_id = obj.parentContainerId
            if parent_id is None:
                continue
            if parent_id == obj.id:
                raise ValueError(f"Object {obj.id} cannot contain itself")
            parent = objects.get(parent_id)
            if parent is None:
                raise ValueError(
                    f"Object {obj.id} references missing semantic parent {parent_id}"
                )
            if not is_container_capable(parent):
                raise ValueError(f"Object {parent_id} is not container-capable")
            if not allowed_parent(semantic_type(obj), semantic_type(parent)):
                raise ValueError(
                    f"Invalid containment: {semantic_type(obj)} in {semantic_type(parent)}"
                )
        for obj in self.canvasObjects:
            visited = {obj.id}
            current = obj
            while current.parentContainerId is not None:
                if current.parentContainerId in visited:
                    raise ValueError(f"Containment cycle involving {obj.id}")
                visited.add(current.parentContainerId)
                current = objects[current.parentContainerId]
        for connector in self.connectors:
            if (
                connector.origin == "containment"
                and connector.container_id not in object_ids
            ):
                raise ValueError(
                    f"Managed connector {connector.id} has no valid container"
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

    service_type: ServiceType
    existing_names: list[str] = Field(default_factory=list)


class ResourceInitializationResponse(BaseModel):
    """Backend-owned initial domain values for a resource."""

    name: str
    config: dict[str, Any]
    terraform_variables: dict[str, Any]
