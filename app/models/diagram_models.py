"""Pydantic input models for diagram state validation.

These models validate incoming diagram state payloads from the frontend.
Element and connector models allow extra fields for extensibility.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ViewportInput(BaseModel):
    """Viewport position and zoom level."""

    x: float
    y: float
    zoom: float


class EnvironmentConfigInput(BaseModel):
    """Environment configuration with optional variables."""

    name: str
    variables: dict[str, str] = {}


class SerializedElementInput(BaseModel):
    """Diagram element — allows extra fields for extensibility."""

    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    x: float
    y: float
    name: str


class SerializedConnectorInput(BaseModel):
    """Diagram connector — allows extra fields for extensibility."""

    model_config = ConfigDict(extra="allow")

    id: str
    sourceId: str
    targetId: str
    type: str


class DiagramStateInput(BaseModel):
    """Top-level diagram state input for save/update endpoints."""

    version: int
    projectName: str
    environments: list[EnvironmentConfigInput]
    elements: list[SerializedElementInput]
    connectors: list[SerializedConnectorInput]
    viewport: ViewportInput
    globalTerraformConfig: dict[str, Any] | None = None
