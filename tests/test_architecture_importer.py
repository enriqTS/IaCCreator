import asyncio

from app.main import import_architecture
from app.models.architecture_import import ArchitectureImportRequest
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.architecture_importer import ArchitectureImporter
from app.services.connection_handlers.registry import resolve_spec
from app.services.diagram_converter import DiagramConverter
from tests.generator_helpers import connection_architecture


def import_payload() -> ArchitectureDescription:
    spec = resolve_spec(ServiceType.VPC, ServiceType.SUBNET, "contains", {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["project_name"] = "imported-network"
    payload["resources"][0]["provider_region"] = "us-west-2"
    payload["resources"][1]["provider_region"] = "us-west-2"
    return ArchitectureDescription.model_validate(payload)


def test_import_infers_region_and_resource_containment_deterministically():
    architecture = import_payload()

    first = ArchitectureImporter().import_architecture(architecture)
    second = ArchitectureImporter().import_architecture(architecture)

    assert first.diagram == second.diagram
    assert first.imported_resource_count == 2
    assert first.inferred_container_count == 2
    objects = {item.name: item for item in first.diagram.canvasObjects}
    vpc = objects["source-resource"]
    subnet = objects["target-resource"]
    assert vpc.presentation == "container"
    assert vpc.parentContainerId == objects["us-west-2"].id
    assert subnet.parentContainerId == vpc.id
    assert first.diagram.connectors[0].origin == "explicit"


def test_imported_diagram_converts_back_to_generation_architecture():
    imported = ArchitectureImporter().import_architecture(import_payload())

    converted = DiagramConverter().convert(imported.diagram)

    assert converted.project_name == "imported-network"
    assert {resource.service_type for resource in converted.resources} == {
        ServiceType.VPC,
        ServiceType.SUBNET,
    }
    assert len(converted.connections) == 1


def test_architecture_import_endpoint_returns_typed_response():
    request = ArchitectureImportRequest(architecture=import_payload())

    response = asyncio.run(import_architecture(request))

    assert response.imported_resource_count == 2
    assert response.diagram.version == 4
