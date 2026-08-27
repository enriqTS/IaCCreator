"""Validation and normalization for semantic containment."""

from hashlib import sha256

from app.models.containment import (
    ContainmentResolution,
    DerivedConnection,
    EffectiveScope,
    InheritedValue,
)
from app.models.diagram_models import DiagramStateInput
from app.models.diagram_state import SerializedConnector
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.containment_catalog import semantic_type


class ContainmentResolver:
    def normalize(
        self, diagram: DiagramStateInput
    ) -> tuple[DiagramStateInput, ContainmentResolution]:
        resolution = self.resolve(diagram)
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
        provider_region = diagram.globalTerraformConfig.provider.region

        for obj in diagram.canvasObjects:
            ancestors = []
            current = obj
            while current.parentContainerId:
                current = objects[current.parentContainerId]
                ancestors.append(current)
            region = provider_region
            az = None
            vpc_id = None
            subnet_id = None
            for ancestor in ancestors:
                kind = semantic_type(ancestor)
                config = getattr(ancestor, "config", {})
                if kind == "region" and config.get("region"):
                    region = config["region"]
                elif kind == "availability-zone" and config.get("availability_zone"):
                    az = config["availability_zone"]
                elif kind == "vpc" and vpc_id is None:
                    vpc_id = ancestor.id
                elif kind == "subnet" and subnet_id is None:
                    subnet_id = ancestor.id
            scopes.append(
                EffectiveScope(
                    object_id=obj.id,
                    region=region,
                    availability_zone=az,
                    vpc_id=vpc_id,
                    subnet_id=subnet_id,
                )
            )
            if (
                obj.objectType == "architecture-block"
                and obj.serviceType.value in {"subnet", "security-group"}
                and vpc_id
            ):
                spec = resolve_spec(ServiceType.VPC, obj.serviceType, "contains", {})
                if spec is not None:
                    identity = f"{vpc_id}:{obj.id}:{spec.connection_type}"
                    derived.append(
                        DerivedConnection(
                            connector_id=f"containment-{sha256(identity.encode()).hexdigest()[:20]}",
                            source_id=vpc_id,
                            target_id=obj.id,
                            connection_type=spec.connection_type,
                            container_id=vpc_id,
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
        return ContainmentResolution(
            effective_scopes=scopes,
            derived_connections=derived,
            inherited_values=inherited,
        )
