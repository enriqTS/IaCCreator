"""Import a generation architecture into canonical semantic canvas state."""

from hashlib import sha256

from app.models.architecture_import import ArchitectureImportResponse
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.containment_catalog import build_containment_catalog
from app.services.diagram_normalizer import DiagramNormalizer


class ArchitectureImporter:
    def import_architecture(
        self, architecture: ArchitectureDescription
    ) -> ArchitectureImportResponse:
        resource_ids = {
            resource.name: resource.id or self._stable_id("resource", resource.name)
            for resource in architecture.resources
        }
        regions = sorted(
            {
                resource.provider_region
                or architecture.global_terraform_config.provider_region
                for resource in architecture.resources
            }
        ) or [architecture.global_terraform_config.provider_region]
        region_ids = {region: self._stable_id("region", region) for region in regions}
        objects = [
            {
                "id": region_ids[region],
                "objectType": "semantic-container",
                "containerType": "region",
                "name": region,
                "x": 360 + index * 760,
                "y": 360,
                "config": {"region": region},
                "visualConfig": {
                    "width": 680,
                    "height": 560,
                    "fillColor": "#172033",
                    "borderColor": "#64748b",
                    "borderWidth": 2,
                },
                "zIndex": index,
            }
            for index, region in enumerate(regions)
        ]
        parent_by_id: dict[str, str] = {}
        container_ids: set[str] = set()
        rules = build_containment_catalog().rules
        resource_by_name = {
            resource.name: resource for resource in architecture.resources
        }
        resource_by_id = {
            resource.id: resource for resource in architecture.resources if resource.id
        }
        resolved_connections = []
        for connection in architecture.connections:
            source = resource_by_id.get(connection.source_id) or resource_by_name.get(
                connection.source
            )
            target = resource_by_id.get(connection.target_id) or resource_by_name.get(
                connection.target
            )
            if source is not None and target is not None:
                resolved_connections.append((connection, source, target))
        resolved_connections.sort(
            key=lambda item: (
                resource_ids[item[1].name],
                resource_ids[item[2].name],
                item[0].connection_type,
            )
        )
        for connection, source, target in resolved_connections:
            spec = resolve_spec(
                source.service_type,
                target.service_type,
                connection.connection_type,
                connection.connection_config,
            )
            if spec is None or source.service_type not in {
                ServiceType.VPC,
                ServiceType.SUBNET,
            }:
                continue
            if not any(
                rule.parent_type == source.service_type.value
                and rule.child_type == target.service_type.value
                and rule.connection_type == spec.connection_type
                for rule in rules
            ):
                continue
            target_id = resource_ids[target.name]
            parent_by_id.setdefault(target_id, resource_ids[source.name])
            container_ids.add(resource_ids[source.name])

        allowed_region_children = {
            rule.child_type for rule in rules if rule.parent_type == "region"
        }
        for resource in architecture.resources:
            resource_id = resource_ids[resource.name]
            if (
                resource_id not in parent_by_id
                and resource.service_type.value in allowed_region_children
            ):
                region = (
                    resource.provider_region
                    or architecture.global_terraform_config.provider_region
                )
                parent_by_id[resource_id] = region_ids[region]

        for index, resource in enumerate(architecture.resources):
            resource_id = resource_ids[resource.name]
            is_container = resource_id in container_ids
            objects.append(
                {
                    "id": resource_id,
                    "objectType": "architecture-block",
                    "serviceType": resource.service_type.value,
                    "name": resource.name,
                    "x": 180 + (index % 4) * 140,
                    "y": 160 + (index // 4) * 140,
                    "config": resource.config.model_dump(
                        mode="json", exclude_none=True
                    ),
                    "terraformVariables": dict(resource.terraform_variables),
                    "visualConfig": {
                        "width": 480 if is_container else 80,
                        "height": 320 if is_container else 80,
                    },
                    "presentation": "container" if is_container else "node",
                    "parentContainerId": parent_by_id.get(resource_id),
                    "zIndex": len(regions) + index,
                }
            )

        connectors = [
            {
                "id": self._stable_id(
                    "connector",
                    connection.source_id or connection.source,
                    connection.target_id or connection.target,
                    connection.connection_type,
                ),
                "sourceId": resource_ids[source.name],
                "targetId": resource_ids[target.name],
                "connectionType": connection.connection_type,
                "connection_config": dict(connection.connection_config),
                "origin": "explicit",
            }
            for connection, source, target in resolved_connections
        ]
        global_config = architecture.global_terraform_config
        state = {
            "version": 4,
            "projectName": architecture.project_name,
            "environments": [
                environment.model_dump(mode="json")
                for environment in architecture.environments
            ],
            "canvasObjects": objects,
            "connectors": connectors,
            "viewport": {},
            "globalTerraformConfig": {
                "backend": {
                    "type": global_config.backend_type,
                    "config": global_config.backend_config,
                },
                "provider": {
                    "region": global_config.provider_region,
                    "profile": global_config.provider_profile,
                },
                "versionConstraints": {
                    "terraformVersion": global_config.terraform_version,
                    "awsProviderVersion": global_config.aws_provider_version,
                },
            },
        }
        diagram = DiagramNormalizer().normalize(state)
        return ArchitectureImportResponse(
            diagram=diagram,
            imported_resource_count=len(architecture.resources),
            inferred_container_count=len(regions) + len(container_ids),
        )

    @staticmethod
    def _stable_id(kind: str, *parts: str) -> str:
        identity = ":".join((kind, *parts))
        return f"import-{kind}-{sha256(identity.encode()).hexdigest()[:16]}"
