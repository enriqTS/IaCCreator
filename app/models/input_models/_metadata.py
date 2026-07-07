"""Terraform field metadata — single source of truth for variable schema annotations.

This module provides the `TerraformField` helper that wraps Pydantic's `Field`
with `json_schema_extra` containing Terraform variable metadata (group, options,
validation rules, conditional visibility, and explicit type override).

Per-service config models annotate their fields with `TerraformField(...)` so
that `BaseServiceConfig.get_variable_schema()` can introspect them and produce
the JSON schema served to the frontend — eliminating the static
`VARIABLE_SCHEMAS` dict.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidationRule(BaseModel):
    """Validation constraints for a variable (min/max bounds, regex pattern, allowed values)."""

    min: int | float | None = None
    max: int | float | None = None
    pattern: str | None = None
    pattern_description: str | None = None
    allowed_values: list[str | int | float | bool] | None = None


class OptionEntry(BaseModel):
    """A predefined selectable option for a variable (value + human-readable label)."""

    value: str | int | float | bool
    label: str
    group: str | None = None


class VisibleWhen(BaseModel):
    """Conditional visibility rule — show this variable only when another field has a specific value."""

    field: str
    equals: str | int | float | bool


class VariableSchemaEntry(BaseModel):
    """Schema definition for a single Terraform variable exposed by a service.

    This is the output format produced by `BaseServiceConfig.get_variable_schema()`
    and served by the `/api/variable-schemas` endpoint.
    """

    name: str
    type: str  # "string" | "number" | "bool" | "map" | "list"
    description: str
    default: str | int | float | bool | None = None
    group: str = "General"
    options: list[OptionEntry] | None = None
    validation: ValidationRule | None = None
    visible_when: VisibleWhen | None = None


# ---------------------------------------------------------------------------
# TerraformField helper
# ---------------------------------------------------------------------------

# Key used in Pydantic's json_schema_extra / Field metadata to store our info
_TF_META_KEY = "terraform_meta"


class TerraformMeta(BaseModel):
    """Internal container for Terraform field metadata stored in Pydantic field info."""

    group: str = "General"
    tf_type: str | None = (
        None  # Explicit Terraform type override (string/number/bool/map/list)
    )
    options: list[OptionEntry] | None = None
    validation: ValidationRule | None = None
    visible_when: VisibleWhen | None = None


def TerraformField(
    default: Any = ...,
    *,
    group: str = "General",
    description: str = "",
    tf_type: str | None = None,
    options: list[OptionEntry] | None = None,
    validation: ValidationRule | None = None,
    visible_when: VisibleWhen | None = None,
    # Pass-through Pydantic Field kwargs
    alias: str | None = None,
    title: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create a Pydantic Field annotated with Terraform variable metadata.

    Usage:
        class LambdaConfig(BaseServiceConfig):
            runtime: Optional[str] = TerraformField(
                None,
                group="General",
                description="Lambda function runtime",
                options=[OptionEntry(value="python3.12", label="Python 3.12")],
            )

    The metadata is stored under `field.json_schema_extra[_TF_META_KEY]` and
    retrieved by `BaseServiceConfig.get_variable_schema()` to build schema entries.
    """
    meta = TerraformMeta(
        group=group,
        tf_type=tf_type,
        options=options,
        validation=validation,
        visible_when=visible_when,
    )

    json_schema_extra = {_TF_META_KEY: meta.model_dump(exclude_none=True)}

    return Field(
        default,
        description=description,
        alias=alias,
        title=title,
        json_schema_extra=json_schema_extra,
        **kwargs,
    )


def get_terraform_meta(field_info: Any) -> TerraformMeta | None:
    """Extract TerraformMeta from a Pydantic FieldInfo, if present.

    Returns None if the field was not annotated with TerraformField.
    """
    extra = getattr(field_info, "json_schema_extra", None)
    if extra is None or not isinstance(extra, dict):
        return None
    raw = extra.get(_TF_META_KEY)
    if raw is None:
        return None
    return TerraformMeta.model_validate(raw)


def _infer_tf_type(annotation: Any) -> str:
    """Infer the Terraform variable type from the Python type annotation."""
    import types
    from typing import get_args, get_origin

    # Unwrap Optional (Union[X, None])
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is type(None):
        # Python 3.10+ X | None
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            annotation = non_none[0]
            origin = get_origin(annotation)

    # Also handle typing.Optional which is Union[X, None]
    if origin is not None:
        import typing

        if origin is typing.Union:
            args = get_args(annotation)
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                annotation = non_none[0]
                origin = get_origin(annotation)

    # Now resolve the actual type
    if annotation is str:
        return "string"
    if annotation is int or annotation is float:
        return "number"
    if annotation is bool:
        return "bool"
    if origin is dict or annotation is dict:
        return "map"
    if origin is list or annotation is list:
        return "list"

    # Fallback
    return "string"
