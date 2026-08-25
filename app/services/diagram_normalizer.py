"""Canonicalization boundary for editor diagram state."""

from typing import Any

from app.models.diagram_state import DiagramState
from app.services.diagram_migrations import migrate_diagram_state


class DiagramNormalizer:
    """Migrate and validate editor state before storage or processing."""

    def normalize(self, state: dict[str, Any]) -> DiagramState:
        return DiagramState.model_validate(migrate_diagram_state(state))
