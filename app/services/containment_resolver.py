"""Validation and normalization for semantic containment."""

from hashlib import sha256

from app.models.containment import (
    ContainmentIssue,
    ContainmentResolution,
    DerivedConnection,
    EffectiveScope,
    EnvironmentScopeView,
    InheritedValue,
)
from app.models.diagram_models import DiagramStateInput
from app.models.diagram_state import SerializedConnector
from app.services.connection_handlers.registry import resolve_spec
from app.services.containment_catalog import semantic_type


class ContainmentResolver:
    def normalize(
        self, diagram: DiagramStateInput
    ) -> tuple[DiagramStateInput, ContainmentResolution]:
        resolution = self.resolve(diagram)
        errors = [issue for issue in resolution.issues if issue.severity == "error"]
        if errors:
            raise ValueError("; ".join(issue.message for issue in errors))
        state = diagram.model_dump(mode="json")
        objects = {obj["id"]: obj for obj in state["canvasObjects"]}

        for inherited in resolution.inherited_values:
            target = objects[inherited.object_id]
            existing = target.get("config", {}).get(inherited.field)
            if existing not in {None, "", inherited.value}:
                raise ValueError(
                    f"{inherited.object_id}.{inherited.field} conflicts with containment"
                )
            target.setdefault("config", {})[inherited.field] = inherited.value

        explicit = [item for item in diagram.connectors if item.origin == "explicit"]
        connectors = [item.model_dump(mode="json") for item in explicit]
        explicit_keys = {
            (item.sourceId, item.targetId, item.connectionType) for item in explicit
        }
        for derived in resolution.derived_connections:
            key = (derived.source_id, derived.target_id, derived.connection_type)
            if key in explicit_keys:
                continue
            connectors.append(
                SerializedConnector(
                    id=derived.connector_id,
                    sourceId=derived.source_id,
                    targetId=derived.target_id,
                    connectionType=derived.connection_type,
                    origin="containment",
                    container_id=derived.container_id,
                ).model_dump(mode="json")
            )
        state["connectors"] = connectors
        return DiagramStateInput.model_validate(state), resolution

    def resolve(self, diagram: DiagramStateInput) -> ContainmentResolution:
        objects = {obj.id: obj for obj in diagram.canvasObjects}
        scopes: list[EffectiveScope] = []
        inherited: list[InheritedValue] = []
        derived: list[DerivedConnection] = []
        issues: list[ContainmentIssue] = []
        provider_region = diagram.globalTerraformConfig.provider.region

        for obj in diagram.canvasObjects:
            ancestors = []
            current = obj
            while current.parentContainerId:
                current = objects[current.parentContainerId]
                ancestors.append(current)
            own_config = getattr(obj, "config", {})
            own_kind = semantic_type(obj)
            region = own_config.get("region") if own_kind == "region" else None
            az = own_config.get("availability_zone")
            vpc_id = None
            subnet_id = None
            for ancestor in ancestors:
                kind = semantic_type(ancestor)
                config = getattr(ancestor, "config", {})
                if kind == "region" and config.get("region") and region is None:
                    region = config["region"]
                elif (
                    kind == "availability-zone"
                    and config.get("availability_zone")
                    and az is None
                ):
                    az = config["availability_zone"]
                elif kind == "vpc" and vpc_id is None:
                    vpc_id = ancestor.id
                elif kind == "subnet" and subnet_id is None:
                    subnet_id = ancestor.id
            region = region or provider_region
            if region != provider_region:
                issues.append(
                    ContainmentIssue(
                        code="region-conflict",
                        message=(
                            f"{obj.id} resolves to Region {region}, but the provider uses "
                            f"{provider_region}"
                        ),
                        object_id=obj.id,
                    )
                )
            if az and not az.startswith(region):
                issues.append(
                    ContainmentIssue(
                        code="availability-zone-conflict",
                        message=f"Availability Zone {az} does not belong to Region {region}",
                        object_id=obj.id,
                    )
                )
            if vpc_id and own_config.get("vpc_id") not in {None, "", vpc_id}:
                issues.append(
                    ContainmentIssue(
                        code="configuration-conflict",
                        message=f"{obj.id}.vpc_id conflicts with containing VPC {vpc_id}",
                        object_id=obj.id,
                        parent_id=vpc_id,
                    )
                )
            scopes.append(
                EffectiveScope(
                    object_id=obj.id,
                    region=region,
                    availability_zone=az,
                    vpc_id=vpc_id,
                    subnet_id=subnet_id,
                )
            )
            if obj.objectType == "architecture-block":
                for ancestor in ancestors:
                    if ancestor.objectType != "architecture-block":
                        continue
                    spec = resolve_spec(
                        ancestor.serviceType, obj.serviceType, "contains", {}
                    )
                    if spec is None:
                        continue
                    identity = f"{ancestor.id}:{obj.id}:{spec.connection_type}"
                    derived.append(
                        DerivedConnection(
                            connector_id=f"containment-{sha256(identity.encode()).hexdigest()[:20]}",
                            source_id=ancestor.id,
                            target_id=obj.id,
                            connection_type=spec.connection_type,
                            container_id=ancestor.id,
                        )
                    )
            if (
                obj.objectType == "architecture-block"
                and obj.serviceType.value == "subnet"
                and az
            ):
                source = next(
                    ancestor.id
                    for ancestor in ancestors
                    if semantic_type(ancestor) == "availability-zone"
                )
                inherited.append(
                    InheritedValue(
                        object_id=obj.id,
                        field="availability_zone",
                        value=az,
                        source_id=source,
                    )
                )
        environment_scopes = [
            EnvironmentScopeView(
                environment=environment.name,
                effective_scopes=[
                    scope.model_copy(
                        update={
                            "region": environment.variables.get("region", scope.region),
                            "availability_zone": environment.variables.get(
                                "availability_zone", scope.availability_zone
                            ),
                        }
                    )
                    for scope in scopes
                ],
            )
            for environment in diagram.environments
        ]
        return ContainmentResolution(
            effective_scopes=scopes,
            environment_scopes=environment_scopes,
            derived_connections=derived,
            inherited_values=inherited,
            issues=issues,
        )
