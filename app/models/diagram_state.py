"""The persisted diagram format — owned by the backend, migrated on read."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CURRENT_DIAGRAM_VERSION = 3

VALID_GEOMETRIC_SHAPES = {
    "rectangle",
    "rounded-rectangle",
    "ellipse",
    "circle",
    "triangle",
    "diamond",
    "parallelogram",
    "trapezoid",
    "hexagon",
    "octagon",
    "pentagon",
    "star",
    "cross",
    "arrow-right",
    "arrow-left",
    "arrow-up",
    "arrow-down",
    "chevron",
    "cylinder",
    "cloud",
    "callout",
    "document",
    "process",
    "decision",
    "data",
    "predefined-process",
}

VALID_UML_KINDS = {
    "class",
    "interface",
    "actor",
    "use-case",
    "component",
    "package",
    "node",
}


class BlockVisual(BaseModel):
    """Visual configuration for an architecture block."""

    width: float = 80
    height: float = 80


class LineVisual(BaseModel):
    """Visual configuration for a line."""

    color: str = "#ffffff"
    borderWidth: float = 2
    strokeStyle: str = "solid"
    startArrow: bool = False
    endArrow: bool = False
    routingMode: str = "orthogonal"


class GeometricVisual(BaseModel):
    """Visual configuration for a geometric shape."""

    width: float = 120
    height: float = 80
    fill: bool = False
    fillColor: str = "#3b82f6"
    borderColor: str = "#ffffff"
    borderWidth: float = 2
    shape: str = "rectangle"


class TextVisual(BaseModel):
    """Visual configuration for a text object."""

    width: float = 50
    height: float = 28
    fontSize: float = 14
    fontColor: str = "#ffffff"
    textAlign: str = "center"
    bold: bool = False
    italic: bool = False


class UMLVisual(BaseModel):
    """Visual configuration for a UML object."""

    width: float = 180
    height: float = 120
    fillColor: str = "#2a2a2a"
    borderColor: str = "#ffffff"
    borderWidth: float = 2
    headerColor: str = "#3b82f6"


VISUAL_MODELS: dict[str, type[BaseModel]] = {
    "architecture-block": BlockVisual,
    "line": LineVisual,
    "geometric": GeometricVisual,
    "text": TextVisual,
    "uml": UMLVisual,
}


class Viewport(BaseModel):
    """Canvas pan and zoom."""

    offsetX: float = 0
    offsetY: float = 0
    scale: float = 1.0


class EnvironmentEntry(BaseModel):
    """A deployment environment as stored in a diagram."""

    name: str
    variables: dict[str, str] = Field(default_factory=dict)


class SerializedObjectGroup(BaseModel):
    """A named group of canvas objects."""

    id: str
    name: str
    memberIds: list[str] = Field(default_factory=list)


class SerializedConnector(BaseModel):
    """A connection between two architecture blocks."""

    model_config = ConfigDict(extra="allow")

    id: str
    sourceId: str
    targetId: str
    connectionType: str = "triggers"
    connectionConfig: dict[str, Any] | None = None


class SerializedCanvasObject(BaseModel):
    """One object on the canvas, in the current storage format."""

    model_config = ConfigDict(extra="allow")

    id: str
    objectType: str
    name: str = ""
    visualConfig: dict[str, Any] = Field(default_factory=dict)
    zIndex: int = 0
    groupId: str | None = None


class DiagramState(BaseModel):
    """A whole saved diagram, at the current format version."""

    model_config = ConfigDict(extra="allow")

    version: Literal[3] = CURRENT_DIAGRAM_VERSION
    projectName: str = ""
    environments: list[EnvironmentEntry] = Field(default_factory=list)
    canvasObjects: list[SerializedCanvasObject] = Field(default_factory=list)
    connectors: list[SerializedConnector] = Field(default_factory=list)
    objectGroups: list[SerializedObjectGroup] = Field(default_factory=list)
    viewport: Viewport = Field(default_factory=Viewport)
    globalRoutingMode: str = "orthogonal"
    globalTerraformConfig: dict[str, Any] | None = None
