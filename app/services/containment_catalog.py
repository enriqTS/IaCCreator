"""Backend-owned semantic containment capabilities."""

from app.models.containment import (
    ContainerTypeDefinition,
    ContainmentCatalogResponse,
    ContainmentOutcome,
    ContainmentRule,
    InheritedFieldRule,
    ServiceContainmentCapability,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec

ARCHITECTURE_BOUNDARY_TYPES = {"organization", "organizational-unit", "account"}
SCOPE_TYPES = {
    "region",
    "availability-zone",
    "generic",
    *ARCHITECTURE_BOUNDARY_TYPES,
}
RESOURCE_CONTAINER_TYPES = {"vpc", "subnet"}
CONTAINER_TYPES = SCOPE_TYPES | RESOURCE_CONTAINER_TYPES

_PARENT_TYPES: dict[str, set[str]] = {
    "organization": {"generic"},
    "organizational-unit": {"organization", "organizational-unit", "generic"},
    "account": {"organization", "organizational-unit", "generic"},
    "region": {"account", "generic"},
    "availability-zone": {"region", "generic"},
    "vpc": {"region", "availability-zone", "generic"},
    "subnet": {"vpc"},
    "security-group": {"vpc", "subnet"},
    "route-table": {"vpc", "subnet"},
    "internet-gateway": {"vpc"},
    "nat-gateway": {"subnet"},
    "target-group": {"vpc"},
    "route53": {"vpc"},
    "ec2": {"subnet"},
    "ecs": {"subnet"},
    "eks": {"subnet"},
    "lambda": {"subnet"},
    "ec2-auto-scaling": {"subnet"},
    "load-balancer": {"subnet"},
    "efs": {"subnet"},
    "memorydb": {"subnet"},
    "database-migration-service": {"subnet"},
    "mq": {"subnet"},
    "mwaa": {"subnet"},
    "network-firewall": {"subnet"},
    "client-vpn": {"subnet"},
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
            container_type="organization",
            display_name="AWS Organization",
            allowed_parent_types=["generic"],
            allowed_child_types=sorted(
                child
                for child, parents in _PARENT_TYPES.items()
                if "organization" in parents
            ),
        ),
        ContainerTypeDefinition(
            container_type="organizational-unit",
            display_name="Organizational Unit",
            allowed_parent_types=["organization", "organizational-unit", "generic"],
            allowed_child_types=sorted(
                child
                for child, parents in _PARENT_TYPES.items()
                if "organizational-unit" in parents
            ),
        ),
        ContainerTypeDefinition(
            container_type="account",
            display_name="AWS Account",
            allowed_parent_types=["organization", "organizational-unit", "generic"],
            allowed_child_types=sorted(
                child
                for child, parents in _PARENT_TYPES.items()
                if "account" in parents
            ),
        ),
        ContainerTypeDefinition(
            container_type="region",
            display_name="AWS Region",
            allowed_parent_types=["generic"],
            allowed_child_types=sorted(
                child for child, parents in _PARENT_TYPES.items() if "region" in parents
            ),
            config_fields=["region"],
        ),
        ContainerTypeDefinition(
            container_type="availability-zone",
            display_name="Availability Zone",
            allowed_parent_types=["region", "generic"],
            allowed_child_types=sorted(
                child
                for child, parents in _PARENT_TYPES.items()
                if "availability-zone" in parents
            ),
            config_fields=["availability_zone"],
        ),
        ContainerTypeDefinition(
            container_type="generic",
            display_name="Architecture boundary",
            allowed_parent_types=sorted(CONTAINER_TYPES),
            allowed_child_types=sorted(_PARENT_TYPES),
        ),
    ]
    capabilities = [
        ServiceContainmentCapability(
            service_type=service.value,
            container_presentation=service in {ServiceType.VPC, ServiceType.SUBNET},
            allowed_parent_types=sorted(_PARENT_TYPES.get(service.value, set())),
            allowed_child_types=sorted(
                child
                for child, parents in _PARENT_TYPES.items()
                if service.value in parents
            ),
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
                    ServiceType(resolved_parent),
                    ServiceType(child),
                    "places"
                    if resolved_parent == "subnet"
                    and child not in {"nat-gateway", "route-table"}
                    else "contains",
                    {},
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
        inherited_fields=[
            InheritedFieldRule(
                field="region",
                source_types=["region"],
                target_types=["availability-zone", "vpc", "subnet"],
                policy="managed",
            ),
            InheritedFieldRule(
                field="availability_zone",
                source_types=["availability-zone"],
                target_types=["subnet"],
                policy="managed",
            ),
            InheritedFieldRule(
                field="vpc_id",
                source_types=["vpc"],
                target_types=["subnet", "security-group"],
                policy="managed",
            ),
        ],
    )
