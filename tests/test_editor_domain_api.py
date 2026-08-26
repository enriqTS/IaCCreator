"""Coverage for backend-owned editor metadata and conversion contracts."""

import asyncio

from app.generators.registry import GENERATOR_REGISTRY
from app.main import (
    app,
    diagram_architecture,
    get_editor_bootstrap,
    initialize_resource,
)
from app.models.diagram_models import DiagramStateInput, ResourceInitializationRequest
from app.models.input_models import ServiceType


def test_bootstrap_matches_generator_registry() -> None:
    """Bootstrap support flags come exclusively from the generator registry."""
    bootstrap = asyncio.run(get_editor_bootstrap())
    supported = {
        ServiceType(entry.service_type)
        for entry in bootstrap.services
        if entry.supported
    }
    assert supported == set(GENERATOR_REGISTRY)
    assert bootstrap.global_terraform_defaults.provider.region == "us-east-1"


def test_resource_initialization_uses_backend_name_and_defaults() -> None:
    """Initialization derives uniqueness and typed variable defaults."""
    result = asyncio.run(
        initialize_resource(
            ResourceInitializationRequest(
                service_type=ServiceType.LAMBDA,
                existing_names=["lambda-1", "lambda-2"],
            )
        )
    )
    assert result.name == "lambda-3"
    assert result.terraform_variables["memory_size"] == 128


def test_diagram_conversion_resolves_ids_and_backend_defaults() -> None:
    """Canonical editor state converts to direct generation input on the server."""
    diagram = DiagramStateInput.model_validate(
        {
            "version": 3,
            "projectName": "project",
            "environments": [],
            "canvasObjects": [
                {
                    "id": "fn",
                    "objectType": "architecture-block",
                    "serviceType": "lambda",
                    "name": "handler",
                    "config": {},
                    "terraformVariables": {},
                    "visualConfig": {},
                },
                {
                    "id": "bucket",
                    "objectType": "architecture-block",
                    "serviceType": "s3",
                    "name": "assets",
                    "config": {},
                    "terraformVariables": {},
                    "visualConfig": {},
                },
            ],
            "connectors": [
                {
                    "id": "connection",
                    "sourceId": "fn",
                    "targetId": "bucket",
                    "connectionType": "writes_to",
                }
            ],
            "viewport": {},
        }
    )
    architecture = asyncio.run(diagram_architecture(diagram))
    assert architecture.environments[0].name == "dev"
    assert architecture.connections[0].source_id == "fn"
    assert architecture.connections[0].target == "assets"


def test_editor_endpoints_are_typed_in_openapi() -> None:
    """Every JSON editor endpoint publishes request and response schemas."""
    document = app.openapi()
    for path, method in {
        "/api/editor-bootstrap": "get",
        "/api/resources/initialize": "post",
        "/api/diagrams/normalize": "post",
        "/api/diagrams/architecture": "post",
        "/api/diagrams/generate/json": "post",
        "/api/diagrams/connections/preview": "post",
        "/api/diagrams/connections/apply": "post",
    }.items():
        operation = document["paths"][path][method]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"]
        if method == "post":
            assert operation["requestBody"]["content"]["application/json"]["schema"]
