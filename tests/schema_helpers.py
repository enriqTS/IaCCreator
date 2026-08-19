"""Access to the variable schemas the backend serves, for tests that assert on them."""

from __future__ import annotations

from app.models.input_models import ServiceType
from app.models.input_models._general import _get_cached_service_config_models
from app.models.input_models._metadata import VariableSchemaEntry


def service_schemas() -> dict[ServiceType, list[VariableSchemaEntry]]:
    """Every service that exposes Terraform variables, mapped to its schema entries."""
    return {
        service_type: config_cls.get_variable_schema()
        for service_type, config_cls in _get_cached_service_config_models().items()
        if config_cls.has_terraform_schema()
    }
