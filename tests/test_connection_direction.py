"""Backend ownership of logical connection direction."""

from app.models.diagram_models import DiagramStateInput


def test_drawn_reverse_connection_is_canonicalized() -> None:
    """A visual line direction does not determine generation direction."""
    diagram = DiagramStateInput.model_validate(
        {
            "version": 3,
            "projectName": "test",
            "environments": [],
            "canvasObjects": [
                {
                    "id": "fn",
                    "objectType": "architecture-block",
                    "serviceType": "lambda",
                    "name": "function",
                    "visualConfig": {},
                },
                {
                    "id": "api",
                    "objectType": "architecture-block",
                    "serviceType": "api-gateway",
                    "name": "api",
                    "visualConfig": {},
                },
            ],
            "connectors": [
                {
                    "id": "connection",
                    "sourceId": "fn",
                    "targetId": "api",
                    "connectionType": "triggers",
                }
            ],
            "viewport": {},
        }
    )
    connector = diagram.connectors[0]
    assert connector.sourceId == "api"
    assert connector.targetId == "fn"
    assert connector.connectionType == "route_handler"
