"""Validation and scope resolution for semantic containment."""

from app.models.containment import ContainmentResolution, EffectiveScope, InheritedValue
from app.models.diagram_models import DiagramStateInput
from app.services.containment_catalog import semantic_type


class ContainmentResolver:
    def resolve(self, diagram: DiagramStateInput) -> ContainmentResolution:
        objects = {obj.id: obj for obj in diagram.canvasObjects}
        scopes: list[EffectiveScope] = []
        inherited: list[InheritedValue] = []
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
                and obj.serviceType.value == "subnet"
                and az
            ):
                inherited.append(
                    InheritedValue(
                        object_id=obj.id,
                        field="availability_zone",
                        value=az,
                        source_id=next(
                            ancestor.id
                            for ancestor in ancestors
                            if semantic_type(ancestor) == "availability-zone"
                        ),
                    )
                )
        return ContainmentResolution(
            effective_scopes=scopes, inherited_values=inherited
        )
