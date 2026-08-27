"""Upgrades stored diagrams to the current format so the API only ever serves one shape."""

from __future__ import annotations

from typing import Any

from app.models.diagram_state import (
    CURRENT_DIAGRAM_VERSION,
    VALID_GEOMETRIC_SHAPES,
    VALID_UML_KINDS,
    VISUAL_MODELS,
)
from app.models.input_models import ServiceType
from app.services.resource_initializer import ResourceInitializer

_initializer = ResourceInitializer()


def _default_terraform_variables(service_type: str) -> dict[str, Any]:
    """Seed legacy blocks from backend-owned resource defaults."""
    try:
        return _initializer.terraform_defaults(ServiceType(service_type))
    except ValueError:
        return {}


def _upgrade_v1_to_v2(state: dict[str, Any]) -> dict[str, Any]:
    """Turn flat `elements` into canvas objects carrying default visuals."""
    objects = []
    for index, element in enumerate(state.get("elements") or []):
        service_type = element.get("serviceType") or element.get("type", "")
        objects.append(
            {
                "id": element.get("id"),
                "objectType": "architecture-block",
                "serviceType": service_type,
                "name": element.get("name", ""),
                "x": (element.get("position") or {}).get("x", 0),
                "y": (element.get("position") or {}).get("y", 0),
                "config": dict(element.get("config") or {}),
                "terraformVariables": _default_terraform_variables(service_type),
                "visualConfig": {},
                "zIndex": index,
            }
        )
    state["canvasObjects"] = objects
    state.pop("elements", None)
    viewport = state.get("viewport") or {}
    if "x" in viewport or "y" in viewport or "zoom" in viewport:
        state["viewport"] = {
            "offsetX": viewport.get("x", 0),
            "offsetY": viewport.get("y", 0),
            "scale": viewport.get("zoom", 1),
        }
    state["version"] = 2
    return state


def _upgrade_v2_to_v3(state: dict[str, Any]) -> dict[str, Any]:
    """Give lines explicit anchors instead of the flat anchor fields v2 used."""
    for obj in state.get("canvasObjects") or []:
        if obj.get("objectType") != "line":
            continue
        obj.setdefault("sourceAnchorObjectId", None)
        obj.setdefault("targetAnchorObjectId", None)
        if obj.get("sourceAnchorObjectId") and not obj.get("sourceAnchorPosition"):
            obj["sourceAnchorPosition"] = "right"
        if obj.get("targetAnchorObjectId") and not obj.get("targetAnchorPosition"):
            obj["targetAnchorPosition"] = "left"
    state["version"] = 3
    return state


def _upgrade_v3_to_v4(state: dict[str, Any]) -> dict[str, Any]:
    """Add semantic hierarchy and connector provenance defaults."""
    objects = state.get("canvasObjects")
    if isinstance(objects, list):
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            obj.setdefault("parentContainerId", None)
            if obj.get("objectType") == "architecture-block":
                obj.setdefault("presentation", "node")
    connectors = state.get("connectors")
    if isinstance(connectors, list):
        for connector in connectors:
            if not isinstance(connector, dict):
                continue
            connector.setdefault("origin", "explicit")
            connector.setdefault("container_id", None)
    state["version"] = 4
    return state


def _normalise(state: dict[str, Any]) -> dict[str, Any]:
    """Fill in visual defaults and replace values the editor would reject."""
    objects = state.get("canvasObjects")
    if not isinstance(objects, list):
        return state
    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            continue
        object_type = obj.get("objectType")
        visual_model = VISUAL_MODELS.get(object_type)
        if visual_model is not None:
            supplied = obj.get("visualConfig") or {}
            obj["visualConfig"] = visual_model.model_validate(supplied).model_dump()

        if obj.get("zIndex") is None:
            obj["zIndex"] = index
        if object_type == "geometric":
            shape = obj["visualConfig"].get("shape")
            if shape not in VALID_GEOMETRIC_SHAPES:
                obj["visualConfig"]["shape"] = "rectangle"
        elif object_type == "uml" and obj.get("umlKind") not in VALID_UML_KINDS:
            obj["umlKind"] = "class"
    return state


_UPGRADES = {1: _upgrade_v1_to_v2, 2: _upgrade_v2_to_v3, 3: _upgrade_v3_to_v4}


def migrate_diagram_state(state: dict[str, Any]) -> dict[str, Any]:
    """Bring a stored diagram up to the current version."""
    if not isinstance(state, dict):
        return state

    migrated = dict(state)
    version = migrated.get("version") or 1
    while version < CURRENT_DIAGRAM_VERSION:
        upgrade = _UPGRADES.get(version)
        if upgrade is None:
            break
        migrated = upgrade(migrated)
        version = migrated.get("version", version + 1)

    migrated["version"] = CURRENT_DIAGRAM_VERSION
    return _normalise(migrated)
