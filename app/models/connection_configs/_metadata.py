"""Field metadata for connection configs — the schema served to the frontend."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.input_models._metadata import OptionEntry, ValidationRule, VisibleWhen

_FIELD_META_KEY = "connection_meta"

FieldType = str


class LinkedEntry(BaseModel):
    """Points a field at an array on the source resource's own config."""

    config_path: str
    display_key: str
    create_template: dict[str, Any] = Field(default_factory=dict)


class ConnectionFieldSchema(BaseModel):
    """One configurable field of a connection, as rendered by the frontend."""

    key: str
    label: str
    type: FieldType
    default: str | int | float | bool | None = None
    placeholder: str | None = None
    options: list[OptionEntry] | None = None
    validation: ValidationRule | None = None
    visible_when: VisibleWhen | None = None
    linked: LinkedEntry | None = None


class ConnectionFieldMeta(BaseModel):
    """Internal container for connection field metadata stored on the Pydantic field."""

    label: str
    type: FieldType = "text"
    placeholder: str | None = None
    options: list[OptionEntry] | None = None
    validation: ValidationRule | None = None
    visible_when: VisibleWhen | None = None
    linked: LinkedEntry | None = None


def ConnectionField(
    default: Any = ...,
    *,
    label: str,
    description: str = "",
    type: FieldType = "text",
    placeholder: str | None = None,
    options: list[OptionEntry] | None = None,
    validation: ValidationRule | None = None,
    visible_when: VisibleWhen | None = None,
    linked: LinkedEntry | None = None,
) -> Any:
    """Declare a user-configurable connection field and how the frontend should render it."""
    meta = ConnectionFieldMeta(
        label=label,
        type=type,
        placeholder=placeholder,
        options=options,
        validation=validation,
        visible_when=visible_when,
        linked=linked,
    )
    # The same rule drives frontend rendering and server-side enforcement
    constraints: dict[str, Any] = {}
    if validation is not None:
        if validation.min is not None:
            constraints["ge"] = validation.min
        if validation.max is not None:
            constraints["le"] = validation.max
        if validation.pattern is not None:
            constraints["pattern"] = validation.pattern
    return Field(
        default,
        description=description,
        json_schema_extra={_FIELD_META_KEY: meta.model_dump(exclude_none=True)},
        **constraints,
    )


def get_connection_meta(field_info: Any) -> ConnectionFieldMeta | None:
    """Return the connection metadata attached to a Pydantic field, if any."""
    extra = getattr(field_info, "json_schema_extra", None)
    if not isinstance(extra, dict):
        return None
    raw = extra.get(_FIELD_META_KEY)
    return ConnectionFieldMeta.model_validate(raw) if raw else None
