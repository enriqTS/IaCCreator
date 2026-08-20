"""Persistence layer data models for user records and diagrams."""

from pydantic import BaseModel, field_validator

from app.services.diagram_migrations import migrate_diagram_state


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

    @field_validator("diagram_state")
    @classmethod
    def upgrade_stored_state(cls, value: dict) -> dict:
        """Records are migrated on read so callers only ever see the current format."""
        return migrate_diagram_state(value)


class DiagramSummary(BaseModel):
    """Lightweight diagram summary for listing endpoints."""

    diagram_id: str
    project_name: str
    updated_at: str  # ISO 8601
