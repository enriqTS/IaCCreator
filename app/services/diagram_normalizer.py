"""Canonicalization boundary for editor diagram state."""

from typing import Any

from app.models.diagram_models import DiagramStateInput
from app.models.diagram_state import DiagramState
from app.services.containment_resolver import ContainmentResolver
from app.services.diagram_migrations import migrate_diagram_state


class DiagramNormalizer:
    """Migrate, fill defaults, and validate editor state."""

    def __init__(self) -> None:
        self._containment = ContainmentResolver()

    def normalize(self, state: dict[str, Any]) -> DiagramStateInput:
        migrated = migrate_diagram_state(state)
        with_defaults = DiagramState.model_validate(migrated).model_dump()
        validated = DiagramStateInput.model_validate(with_defaults)
        normalized, _ = self._containment.normalize(validated)
        return normalized
