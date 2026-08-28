import pytest

from app.exceptions import CrossRegionConnectionError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def architecture_for(source: ServiceType, target: ServiceType, connection_type: str):
    spec = resolve_spec(source, target, connection_type, {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "us-west-2"
    return ArchitectureDescription.model_validate(payload)


def test_rejects_cross_region_connection_for_same_region_spec():
    architecture = architecture_for(ServiceType.SUBNET, ServiceType.LAMBDA, "places")

    with pytest.raises(CrossRegionConnectionError, match="cannot use 'places'"):
        IRBuilder().build(architecture)


def test_allows_cross_region_connection_when_registry_policy_permits_it():
    architecture = architecture_for(
        ServiceType.LAMBDA, ServiceType.DYNAMODB, "accesses"
    )

    project = IRBuilder().build(architecture)

    assert project.connections[0].connection_type == "accesses"
