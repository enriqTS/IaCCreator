"""Canonicalization boundary for editor diagram state."""

from typing import Any

from app.models.diagram_models import DiagramStateInput
from app.models.diagram_state import DiagramState
from app.services.diagram_migrations import migrate_diagram_state


class DiagramNormalizer:
    """Migrate, fill defaults, and validate editor state."""

    def normalize(self, state: dict[str, Any]) -> DiagramStateInput:
        migrated = migrate_diagram_state(state)
        with_defaults = DiagramState.model_validate(migrated).model_dump()
        return DiagramStateInput.model_validate(with_defaults)
