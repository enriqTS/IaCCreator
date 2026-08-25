"""Tests for backend-owned linked connection mutations."""

from app.models.connection_operations import (
    CreateLinkedEntry,
    RemoveLinkedEntry,
    UpdateLinkedEntry,
)
from app.models.diagram_models import DiagramStateInput
from app.services.connection_operation_service import ConnectionOperationService


def diagram() -> DiagramStateInput:
    """Return an API Gateway to Lambda editor diagram."""
    return DiagramStateInput.model_validate(
        {
            "version": 3,
            "projectName": "test",
            "environments": [],
            "canvasObjects": [
                {
                    "id": "api",
                    "objectType": "architecture-block",
                    "name": "api",
                    "serviceType": "api-gateway",
                    "config": {"routes": []},
                    "visualConfig": {},
                },
                {
                    "id": "fn",
                    "objectType": "architecture-block",
                    "name": "handler",
                    "serviceType": "lambda",
                    "config": {},
                    "visualConfig": {},
                },
            ],
            "connectors": [
                {
                    "id": "connection",
                    "sourceId": "api",
                    "targetId": "fn",
                    "connectionType": "triggers",
                    "connection_config": {"connection_role": "route_handler"},
                }
            ],
            "viewport": {},
        }
    )


def test_create_update_remove_linked_entry() -> None:
    """Linked entry semantics and target binding are registry-owned."""
    service = ConnectionOperationService()
    created = service.apply(
        diagram(),
        CreateLinkedEntry(
            operation="create",
            connector_id="connection",
            field_key="route_path",
            display_value="/users",
            entry_values={"methods": ["GET"]},
        ),
    )
    route = created.canvasObjects[0].model_extra["config"]["routes"][0]
    assert route["integration_id"] == "fn"
    assert route["integration_name"] == "handler"
    assert route["methods"] == ["GET"]

    updated = service.apply(
        created,
        UpdateLinkedEntry(
            operation="update",
            connector_id="connection",
            field_key="route_path",
            display_value="/users",
            entry_field_key="methods",
            entry_field_value=["POST"],
        ),
    )
    assert updated.canvasObjects[0].model_extra["config"]["routes"][0]["methods"] == [
        "POST"
    ]

    removed = service.apply(
        updated,
        RemoveLinkedEntry(
            operation="remove",
            source_block_id="api",
            field_key="route_path",
            display_value="/users",
        ),
    )
    assert removed.canvasObjects[0].model_extra["config"]["routes"] == []
