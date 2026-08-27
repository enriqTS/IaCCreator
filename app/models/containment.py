"""Typed contracts for semantic containment."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ContainmentOutcome(StrEnum):
    CONNECTION = "terraform-connection"
    INHERITED_SCOPE = "inherited-scope"
    VISUAL_ONLY = "visual-only"


class ContainerTypeDefinition(BaseModel):
    container_type: str
    display_name: str
    allowed_parent_types: list[str] = Field(default_factory=list)
    allowed_child_types: list[str] = Field(default_factory=list)
    config_fields: list[str] = Field(default_factory=list)


class ServiceContainmentCapability(BaseModel):
    service_type: str
    container_presentation: bool = False
    allowed_parent_types: list[str] = Field(default_factory=list)
    allowed_child_types: list[str] = Field(default_factory=list)
    allowed_lifecycles: list[str] = Field(
        default_factory=lambda: ["active", "deprecated"]
    )


class ContainmentRule(BaseModel):
    child_type: str
    parent_type: str
    resolved_ancestor_type: str | None = None
    connection_type: str | None = None
    inherited_fields: list[str] = Field(default_factory=list)
    outcome: ContainmentOutcome


class InheritedFieldRule(BaseModel):
    field: str
    source_types: list[str]
    target_types: list[str]
    policy: Literal["managed", "overridable", "external-fallback"]


class ContainmentCatalogResponse(BaseModel):
    container_types: list[ContainerTypeDefinition]
    service_capabilities: list[ServiceContainmentCapability]
    rules: list[ContainmentRule]
    inherited_fields: list[InheritedFieldRule]


class ContainmentIssue(BaseModel):
    code: str
    message: str
    object_id: str | None = None
    parent_id: str | None = None
    severity: Literal["error", "warning"] = "error"


class EffectiveScope(BaseModel):
    object_id: str
    region: str | None = None
    availability_zone: str | None = None
    vpc_id: str | None = None
    subnet_id: str | None = None


class InheritedValue(BaseModel):
    object_id: str
    field: str
    value: Any
    source_id: str
    policy: Literal["managed", "overridable", "external-fallback"] = "managed"


class DerivedConnection(BaseModel):
    connector_id: str
    source_id: str
    target_id: str
    connection_type: str
    container_id: str


class ContainmentResolution(BaseModel):
    effective_scopes: list[EffectiveScope] = Field(default_factory=list)
    derived_connections: list[DerivedConnection] = Field(default_factory=list)
    inherited_values: list[InheritedValue] = Field(default_factory=list)
    issues: list[ContainmentIssue] = Field(default_factory=list)


class ContainmentOperation(BaseModel):
    operation: Literal[
        "assign", "remove", "move-subtree", "set-scope", "set-presentation"
    ]
    object_id: str
    parent_id: str | None = None
    presentation: Literal["node", "container"] | None = None
    config: dict[str, Any] = Field(default_factory=dict)
