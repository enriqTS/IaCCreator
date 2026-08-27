"""Applies semantic containment intents at the backend boundary."""

from app.models.containment import ContainmentOperation
from app.models.containment_operations import ApplyContainmentOperationResponse
from app.models.diagram_models import DiagramStateInput
from app.services.containment_resolver import ContainmentResolver


class ContainmentOperationService:
    def __init__(self) -> None:
        self._resolver = ContainmentResolver()

    def apply(
        self, diagram: DiagramStateInput, operation: ContainmentOperation
    ) -> ApplyContainmentOperationResponse:
        state = diagram.model_dump(mode="json")
        objects = {obj["id"]: obj for obj in state["canvasObjects"]}
        target = objects.get(operation.object_id)
        if target is None:
            raise ValueError(f"Unknown object {operation.object_id}")

        if operation.operation in {"assign", "move-subtree"}:
            target["parentContainerId"] = operation.parent_id
        elif operation.operation == "remove":
            target["parentContainerId"] = None
        elif operation.operation == "set-presentation":
            if target.get("objectType") != "architecture-block":
                raise ValueError("Only resources support presentation changes")
            target["presentation"] = operation.presentation
        elif operation.operation == "set-scope":
            target["config"] = {**target.get("config", {}), **operation.config}

        validated = DiagramStateInput.model_validate(state)
        normalized, resolution = self._resolver.normalize(validated)
        return ApplyContainmentOperationResponse(
            diagram=normalized,
            resolution=resolution,
        )
