"""Schema-based validation for ResourceConfig values against VARIABLE_SCHEMAS constraints."""

import re

from fastapi import HTTPException

from app.generators.variable_schemas import VARIABLE_SCHEMAS, VariableSchemaEntry
from app.models.input_models import ResourceConfig, ServiceType
from app.models.input_models._base import BaseServiceConfig


def validate_config_against_schema(
    service_type: ServiceType, config: ResourceConfig | BaseServiceConfig
) -> None:
    """Validate a config against schema constraints.

    If the config is a BaseServiceConfig with TerraformField annotations, schema
    entries are introspected from the model. Otherwise, falls back to the static
    VARIABLE_SCHEMAS dictionary.

    Iterates over each schema entry, evaluates visible_when conditions, and checks
    validation rules. Raises HTTPException(422) on the first constraint violation.
    """
    if isinstance(config, BaseServiceConfig) and config.has_terraform_schema():
        entries = type(config).get_variable_schema()
    else:
        entries = VARIABLE_SCHEMAS.get(service_type, [])

    for entry in entries:
        # Evaluate visible_when — skip validation for hidden fields
        if entry.visible_when is not None:
            condition_field_value = getattr(config, entry.visible_when.field, None)
            if condition_field_value != entry.visible_when.equals:
                continue

        value = getattr(config, entry.name, None)

        # Skip if no value set or no validation rule
        if value is None or entry.validation is None:
            continue

        _validate_entry(service_type, entry, value)


def _validate_entry(
    service_type: ServiceType,
    entry: VariableSchemaEntry,
    value: object,
) -> None:
    """Check a single value against its schema entry's validation rule."""
    rule = entry.validation
    label = f"Variable '{entry.name}' for {service_type.value}"

    if rule.min is not None and value < rule.min:
        raise HTTPException(
            status_code=422,
            detail=f"{label}: value {value} is below minimum {rule.min}",
        )

    if rule.max is not None and value > rule.max:
        raise HTTPException(
            status_code=422,
            detail=f"{label}: value {value} exceeds maximum {rule.max}",
        )

    if rule.allowed_values is not None and value not in rule.allowed_values:
        raise HTTPException(
            status_code=422,
            detail=f"{label}: value {value} is not in allowed values {rule.allowed_values}",
        )

    if rule.pattern is not None and isinstance(value, str):
        if not re.match(rule.pattern, value):
            desc = rule.pattern_description or rule.pattern
            raise HTTPException(
                status_code=422,
                detail=f"{label}: value '{value}' does not match pattern: {desc}",
            )
