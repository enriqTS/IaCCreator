"""Conversion from canonical editor state to generation input."""

from app.models.diagram_state import DiagramState
from app.models.input_models import ArchitectureDescription


class DiagramConverter:
    """Build generation input without exposing domain mapping to the browser."""

    def convert(self, diagram: DiagramState) -> ArchitectureDescription:
        blocks = {
            obj.id: obj
            for obj in diagram.canvasObjects
            if obj.objectType == "architecture-block"
        }
        resources = [
            {
                "id": obj.id,
                "name": obj.name,
                "service_type": obj.model_extra.get("serviceType"),
                "config": obj.model_extra.get("config") or {},
                "terraform_variables": obj.model_extra.get("terraformVariables") or {},
            }
            for obj in blocks.values()
        ]
        connections = [
            {
                "source": blocks[connector.sourceId].name,
                "target": blocks[connector.targetId].name,
                "source_id": connector.sourceId,
                "target_id": connector.targetId,
                "connection_type": connector.connectionType,
                "connection_config": connector.model_extra.get("connection_config")
                or connector.connectionConfig
                or {},
            }
            for connector in diagram.connectors
            if connector.sourceId in blocks and connector.targetId in blocks
        ]
        global_config = diagram.globalTerraformConfig or {}
        backend = global_config.get("backend", {})
        provider = global_config.get("provider", {})
        versions = global_config.get("versionConstraints", {})
        return ArchitectureDescription.model_validate(
            {
                "project_name": diagram.projectName or "my-project",
                "environments": [entry.model_dump() for entry in diagram.environments]
                or [{"name": "dev", "variables": {}}],
                "resources": resources,
                "connections": connections,
                "global_terraform_config": {
                    "backend_type": backend.get("type", "local"),
                    "backend_config": backend.get("config", {}),
                    "provider_region": provider.get("region", "us-east-1"),
                    "provider_profile": provider.get("profile"),
                    "terraform_version": versions.get("terraformVersion"),
                    "aws_provider_version": versions.get("awsProviderVersion"),
                },
            }
        )
