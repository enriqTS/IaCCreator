"""Applies semantic containment intents at the backend boundary."""

from pydantic import ValidationError

from app.models.containment import ContainmentIssue, ContainmentOperation
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
            return self._rejected(
                diagram,
                ContainmentIssue(
                    code="missing-object",
                    message=f"Unknown object {operation.object_id}",
                    object_id=operation.object_id,
                ),
            )

        if operation.operation in {"assign", "move-subtree"}:
            target["parentContainerId"] = operation.parent_id
        elif operation.operation == "remove":
            target["parentContainerId"] = None
        elif operation.operation == "set-presentation":
            if target.get("objectType") != "architecture-block":
                return self._rejected(
                    diagram,
                    ContainmentIssue(
                        code="unsupported-presentation",
                        message="Only resources support presentation changes",
                        object_id=operation.object_id,
                    ),
                )
            target["presentation"] = operation.presentation
        elif operation.operation == "set-scope":
            target["config"] = {**target.get("config", {}), **operation.config}

        try:
            validated = DiagramStateInput.model_validate(state)
            normalized, resolution = self._resolver.normalize(validated)
        except (ValidationError, ValueError) as exc:
            return self._rejected(diagram, self._validation_issue(operation, exc))
        return ApplyContainmentOperationResponse(
            diagram=normalized,
            resolution=resolution,
        )

    def _rejected(
        self, diagram: DiagramStateInput, issue: ContainmentIssue
    ) -> ApplyContainmentOperationResponse:
        resolution = self._resolver.resolve(diagram)
        resolution.issues.append(issue)
        return ApplyContainmentOperationResponse(diagram=diagram, resolution=resolution)

    @staticmethod
    def _validation_issue(
        operation: ContainmentOperation, exc: ValidationError | ValueError
    ) -> ContainmentIssue:
        message = str(exc)
        if "cycle" in message or "contain itself" in message:
            code = "containment-cycle"
        elif "container-capable" in message or "Invalid containment" in message:
            code = "invalid-parent-type"
        elif "Availability Zone" in message or "availability_zone" in message:
            code = "availability-zone-conflict"
        elif "Region" in message or "region" in message:
            code = "region-conflict"
        elif "conflict" in message:
            code = "configuration-conflict"
        else:
            code = "unsupported-placement"
        return ContainmentIssue(
            code=code,
            message=message,
            object_id=operation.object_id,
            parent_id=operation.parent_id,
        )
