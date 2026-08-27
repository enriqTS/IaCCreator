"""Backend-owned semantic containment capabilities."""

from app.models.containment import (
    ContainerTypeDefinition,
    ContainmentCatalogResponse,
    ContainmentOutcome,
    ContainmentRule,
    ServiceContainmentCapability,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec

SCOPE_TYPES = {"region", "availability-zone", "generic"}
RESOURCE_CONTAINER_TYPES = {"vpc", "subnet"}
CONTAINER_TYPES = SCOPE_TYPES | RESOURCE_CONTAINER_TYPES

_PARENT_TYPES: dict[str, set[str]] = {
    "region": {"generic"},
    "availability-zone": {"region", "generic"},
    "vpc": {"region", "availability-zone", "generic"},
    "subnet": {"vpc"},
    "security-group": {"vpc", "subnet"},
    "route-table": {"vpc", "subnet"},
    "internet-gateway": {"vpc"},
    "nat-gateway": {"subnet"},
    "target-group": {"vpc"},
    "ec2": {"subnet"},
    "ecs": {"subnet"},
    "eks": {"subnet"},
    "lambda": {"subnet"},
}


def semantic_type(obj: object) -> str:
    if getattr(obj, "objectType", None) == "semantic-container":
        return obj.containerType  # type: ignore[attr-defined]
    service = getattr(obj, "serviceType", None)
    return service.value if service is not None else "visual"


def is_container_capable(obj: object) -> bool:
    if getattr(obj, "objectType", None) == "semantic-container":
        return True
    return (
        semantic_type(obj) in RESOURCE_CONTAINER_TYPES
        and getattr(obj, "presentation", "node") == "container"
    )


def allowed_parent(child_type: str, parent_type: str) -> bool:
    if child_type == "generic":
        return parent_type in CONTAINER_TYPES
    return parent_type in _PARENT_TYPES.get(child_type, set())


def build_containment_catalog() -> ContainmentCatalogResponse:
    definitions = [
        ContainerTypeDefinition(
            container_type="region",
            display_name="AWS Region",
            allowed_parent_types=["generic"],
            config_fields=["region"],
        ),
        ContainerTypeDefinition(
            container_type="availability-zone",
            display_name="Availability Zone",
            allowed_parent_types=["region", "generic"],
            config_fields=["availability_zone"],
        ),
        ContainerTypeDefinition(
            container_type="generic",
            display_name="Architecture boundary",
            allowed_parent_types=sorted(CONTAINER_TYPES),
        ),
    ]
    capabilities = [
        ServiceContainmentCapability(
            service_type=service.value,
            container_presentation=service in {ServiceType.VPC, ServiceType.SUBNET},
            allowed_parent_types=sorted(_PARENT_TYPES.get(service.value, set())),
        )
        for service in ServiceType
        if service.value in _PARENT_TYPES
        or service in {ServiceType.VPC, ServiceType.SUBNET}
    ]
    rules = []
    for child, parents in _PARENT_TYPES.items():
        for parent in sorted(parents):
            resolved_parent = "vpc" if child == "security-group" else parent
            try:
                spec = resolve_spec(
                    ServiceType(resolved_parent), ServiceType(child), "contains", {}
                )
            except ValueError:
                spec = None
            rules.append(
                ContainmentRule(
                    child_type=child,
                    parent_type=parent,
                    resolved_ancestor_type=(
                        "vpc" if child == "security-group" else None
                    ),
                    connection_type=(spec.connection_type if spec else None),
                    inherited_fields=(
                        ["availability_zone"] if child == "subnet" else ["region"]
                    ),
                    outcome=(
                        ContainmentOutcome.CONNECTION
                        if spec
                        else ContainmentOutcome.INHERITED_SCOPE
                        if child in {"availability-zone", "vpc", "subnet"}
                        else ContainmentOutcome.VISUAL_ONLY
                    ),
                )
            )
    return ContainmentCatalogResponse(
        container_types=definitions,
        service_capabilities=capabilities,
        rules=rules,
    )
