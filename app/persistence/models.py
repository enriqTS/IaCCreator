"""Persistence layer data models for user records and diagrams."""

from pydantic import BaseModel


class UserRecord(BaseModel):
    """User session metadata stored in the persistence layer."""

    session_id: str
    created_at: str  # ISO 8601
    last_active: str  # ISO 8601


class DiagramRecord(BaseModel):
    """Full diagram record stored in the persistence layer."""

    diagram_id: str
    session_id: str
    project_name: str
    diagram_state: dict
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601


class DiagramSummary(BaseModel):
    """Lightweight diagram summary for listing endpoints."""

    diagram_id: str
    project_name: str
    updated_at: str  # ISO 8601
