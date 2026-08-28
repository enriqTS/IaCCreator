"""The persisted diagram format — owned by the backend, migrated on read."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.models.input_models import ServiceType

CURRENT_DIAGRAM_VERSION = 4

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


class ContainerVisual(BaseModel):
    """Visual configuration for a semantic boundary."""

    width: float = 480
    height: float = 320
    fillColor: str = "#172033"
    borderColor: str = "#64748b"
    borderWidth: float = 2


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
    "semantic-container": ContainerVisual,
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

    id: str
    sourceId: str
    targetId: str
    connectionType: str = "triggers"
    origin: Literal["explicit", "containment"] = "explicit"
    container_id: str | None = None
    connection_config: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("connection_config", "connectionConfig"),
    )


class CanvasObjectBase(BaseModel):
    """Fields shared by every persisted canvas object."""

    id: str
    objectType: str
    name: str = ""
    visualConfig: dict[str, Any] = Field(default_factory=dict)
    zIndex: int = 0
    groupId: str | None = None
    parentContainerId: str | None = None
    locked: bool = False
    collapsed: bool = False


class ArchitectureBlockObject(CanvasObjectBase):
    """A generated AWS resource on the canvas."""

    objectType: Literal["architecture-block"]
    visualConfig: BlockVisual = Field(default_factory=BlockVisual)
    serviceType: ServiceType
    x: float = 0
    y: float = 0
    config: dict[str, Any] = Field(default_factory=dict)
    terraformVariables: dict[str, str | int | float | bool] = Field(
        default_factory=dict
    )
    presentation: Literal["node", "container"] = "node"


class Point(BaseModel):
    """A serialized canvas point."""

    x: float
    y: float


class LineObject(CanvasObjectBase):
    """A visual line with optional anchors and waypoints."""

    objectType: Literal["line"]
    visualConfig: LineVisual = Field(default_factory=LineVisual)
    startX: float = 0
    startY: float = 0
    endX: float = 0
    endY: float = 0
    sourceAnchorObjectId: str | None = None
    targetAnchorObjectId: str | None = None
    sourceAnchorPosition: str | None = None
    targetAnchorPosition: str | None = None
    waypoints: list[Point] = Field(default_factory=list)


class PositionedObject(CanvasObjectBase):
    """A non-resource object positioned by one point."""

    x: float = 0
    y: float = 0


class GeometricObject(PositionedObject):
    """A geometric canvas shape."""

    objectType: Literal["geometric"]
    visualConfig: GeometricVisual = Field(default_factory=GeometricVisual)


class TextObject(PositionedObject):
    """A text canvas object."""

    objectType: Literal["text"]
    visualConfig: TextVisual = Field(default_factory=TextVisual)
    content: str = ""


class UMLClassData(BaseModel):
    """UML class compartment content."""

    stereotype: str | None = None
    attributes: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)


class UMLObject(PositionedObject):
    """A UML canvas object."""

    objectType: Literal["uml"]
    visualConfig: UMLVisual = Field(default_factory=UMLVisual)
    umlKind: str = "class"
    classData: UMLClassData | None = None


class SemanticContainerObject(PositionedObject):
    """A deployment scope or visual semantic boundary."""

    objectType: Literal["semantic-container"]
    containerType: str
    config: dict[str, Any] = Field(default_factory=dict)
    visualConfig: ContainerVisual = Field(default_factory=ContainerVisual)


SerializedCanvasObject = Annotated[
    ArchitectureBlockObject
    | LineObject
    | GeometricObject
    | TextObject
    | UMLObject
    | SemanticContainerObject,
    Field(discriminator="objectType"),
]


class GlobalBackendConfig(BaseModel):
    """Terraform backend settings persisted by the editor."""

    type: str = "local"
    config: dict[str, str] = Field(default_factory=dict)

    @field_validator("type", mode="before")
    @classmethod
    def fill_type(cls, value: object) -> object:
        """Replace uninitialized editor state with the canonical default."""
        return value or "local"


class GlobalProviderConfig(BaseModel):
    """AWS provider settings persisted by the editor."""

    region: str = "us-east-1"
    profile: str | None = None

    @field_validator("region", mode="before")
    @classmethod
    def fill_region(cls, value: object) -> object:
        """Replace uninitialized editor state with the canonical default."""
        return value or "us-east-1"


class GlobalVersionConstraints(BaseModel):
    """Terraform and provider version constraints."""

    terraformVersion: str | None = None
    awsProviderVersion: str | None = None


class GlobalEnvironmentOverride(BaseModel):
    """Environment-specific global variable overrides."""

    name: str
    variableOverrides: dict[str, str] = Field(default_factory=dict)


class GlobalVariable(BaseModel):
    """A user-defined global Terraform variable."""

    name: str
    type: str
    description: str = ""
    default: str | None = None


class GlobalTerraformConfigState(BaseModel):
    """Canonical persisted global Terraform configuration."""

    backend: GlobalBackendConfig = Field(default_factory=GlobalBackendConfig)
    provider: GlobalProviderConfig = Field(default_factory=GlobalProviderConfig)
    versionConstraints: GlobalVersionConstraints = Field(
        default_factory=GlobalVersionConstraints
    )
    environments: list[GlobalEnvironmentOverride] = Field(default_factory=list)
    globalVariables: list[GlobalVariable] = Field(default_factory=list)


class DiagramState(BaseModel):
    """A whole saved diagram, at the current format version."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[4] = CURRENT_DIAGRAM_VERSION
    projectName: str = ""
    environments: list[EnvironmentEntry] = Field(default_factory=list)
    canvasObjects: list[SerializedCanvasObject] = Field(default_factory=list)
    connectors: list[SerializedConnector] = Field(default_factory=list)
    objectGroups: list[SerializedObjectGroup] = Field(default_factory=list)
    viewport: Viewport = Field(default_factory=Viewport)
    globalRoutingMode: str = "orthogonal"
    globalTerraformConfig: GlobalTerraformConfigState = Field(
        default_factory=GlobalTerraformConfigState
    )
