"""Typed editor bootstrap contracts."""

from enum import StrEnum

from pydantic import BaseModel

from app.models.connection_configs.schema_models import ConnectionSchemaEntry
from app.models.containment import ContainmentCatalogResponse
from app.models.diagram_state import GlobalTerraformConfigState
from app.models.input_models._metadata import VariableSchemaEntry
from app.models.response_models import NamingRulesResponse


class ServiceLifecycle(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    DECORATIVE = "decorative"


class ServiceClassification(StrEnum):
    RESOURCE = "resource"
    CAPABILITY = "capability"
    COMPOSITE = "composite"
    DECORATIVE = "decorative"
    LEGACY = "legacy"


class ServiceCapabilitiesResponse(BaseModel):
    """Editor capabilities for one AWS service."""

    diagram: bool
    terraform: bool
    configurable: bool
    connectable: bool


class ServiceCatalogEntry(BaseModel):
    """Backend support metadata for one AWS service."""

    service_type: str
    display_name: str
    category: str
    classification: ServiceClassification
    lifecycle: ServiceLifecycle
    capabilities: ServiceCapabilitiesResponse


class EditorBootstrapResponse(BaseModel):
    """Domain metadata required to start the editor."""

    services: list[ServiceCatalogEntry]
    variable_schemas: dict[str, list[VariableSchemaEntry]]
    connection_schemas: list[ConnectionSchemaEntry]
    naming_rules: NamingRulesResponse
    global_terraform_defaults: GlobalTerraformConfigState
    diagram_version: int
    containment: ContainmentCatalogResponse
