"""Models describing what a connection contributes, for the editor to display."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PreviewResource(BaseModel):
    """One Terraform resource a connection emits."""

    module: str
    resource_type: str
    resource_name: str


class PreviewGrant(BaseModel):
    """One IAM statement a connection attaches to a resource's execution role."""

    role_owner: str
    effect: str
    actions: list[str]
    resources: list[str]


class ConnectionIssue(BaseModel):
    """Something wrong with a connection that generation still accepts."""

    severity: Literal["error", "warning"]
    message: str


class ConnectionPreview(BaseModel):
    """Everything one connection contributes, plus what is wrong with it."""

    source: str
    target: str
    source_id: str | None = None
    target_id: str | None = None
    connection_type: str
    label: str
    resources: list[PreviewResource] = Field(default_factory=list)
    iam: list[PreviewGrant] = Field(default_factory=list)
    issues: list[ConnectionIssue] = Field(default_factory=list)


class ConnectionPreviewResponse(BaseModel):
    """A preview for every connection in the submitted architecture."""

    previews: list[ConnectionPreview] = Field(default_factory=list)
