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
from app.models.editor_models import ServiceClassification, ServiceLifecycle
from app.models.input_models import ServiceType, get_service_config_models
from app.services.connection_handlers.registry import CONNECTION_SPECS
from app.services.service_catalog import SERVICE_CATALOG


def test_bootstrap_matches_backend_capability_registry() -> None:
    """Bootstrap exposes the complete backend-owned capability catalog."""
    bootstrap = asyncio.run(get_editor_bootstrap())
    entries = {ServiceType(entry.service_type): entry for entry in bootstrap.services}
    assert set(entries) == set(ServiceType)
    assert {
        service for service, entry in entries.items() if entry.capabilities.terraform
    } == set(GENERATOR_REGISTRY)
    assert bootstrap.global_terraform_defaults.provider.region == "us-east-1"
    assert (
        entries[ServiceType.CODECOMMIT].classification == ServiceClassification.LEGACY
    )
    assert not entries[ServiceType.CODECOMMIT].capabilities.diagram
    assert (
        entries[ServiceType.CLEAN_ROOMS].classification
        == ServiceClassification.CAPABILITY
    )
    assert entries[ServiceType.CLEAN_ROOMS].capabilities.diagram


def test_service_catalog_registries_are_consistent() -> None:
    """Every service has an intentional classification and coherent capabilities."""
    assert set(SERVICE_CATALOG) == set(ServiceType)
    config_models = get_service_config_models()
    connected = {spec.source for spec in CONNECTION_SPECS} | {
        spec.target for spec in CONNECTION_SPECS
    }
    for service, metadata in SERVICE_CATALOG.items():
        assert metadata.category
        assert isinstance(metadata.classification, ServiceClassification)
        assert metadata.capabilities.terraform == (service in GENERATOR_REGISTRY)
        assert metadata.capabilities.configurable == (
            service in config_models and service in GENERATOR_REGISTRY
        )
        assert metadata.capabilities.connectable == (service in connected)
        if metadata.classification == ServiceClassification.RESOURCE:
            assert service in GENERATOR_REGISTRY
        if (
            service not in GENERATOR_REGISTRY
            and metadata.lifecycle == ServiceLifecycle.ACTIVE
        ):
            assert metadata.classification in {
                ServiceClassification.CAPABILITY,
                ServiceClassification.COMPOSITE,
            }
            assert metadata.capabilities.diagram
        if metadata.lifecycle in {
            ServiceLifecycle.RETIRED,
            ServiceLifecycle.DECORATIVE,
        }:
            assert not metadata.capabilities.diagram


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
