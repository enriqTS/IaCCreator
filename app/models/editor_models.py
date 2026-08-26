"""Typed editor bootstrap contracts."""

from pydantic import BaseModel

from app.models.connection_configs.schema_models import ConnectionSchemaEntry
from app.models.diagram_state import GlobalTerraformConfigState
from app.models.input_models._metadata import VariableSchemaEntry
from app.models.response_models import NamingRulesResponse


class ServiceCatalogEntry(BaseModel):
    """Backend support metadata for one AWS service."""

    service_type: str
    display_name: str
    category: str = "AWS"
    supported: bool


class EditorBootstrapResponse(BaseModel):
    """Domain metadata required to start the editor."""

    services: list[ServiceCatalogEntry]
    variable_schemas: dict[str, list[VariableSchemaEntry]]
    connection_schemas: list[ConnectionSchemaEntry]
    naming_rules: NamingRulesResponse
    global_terraform_defaults: GlobalTerraformConfigState
    diagram_version: int
