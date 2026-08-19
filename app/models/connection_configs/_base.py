"""Base class for every connection's typed configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.connection_configs._metadata import (
    ConnectionFieldSchema,
    get_connection_meta,
)


class BaseConnectionConfig(BaseModel):
    """Typed configuration for one kind of connection between two services."""

    # Unknown keys are rejected so a typo surfaces as a 422 instead of a silent default
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def get_field_schema(cls) -> list[ConnectionFieldSchema]:
        """Describe the user-configurable fields for the frontend to render."""
        entries: list[ConnectionFieldSchema] = []
        for name, field_info in cls.model_fields.items():
            meta = get_connection_meta(field_info)
            if meta is None:
                continue
            default = field_info.default
            entries.append(
                ConnectionFieldSchema(
                    key=name,
                    label=meta.label,
                    type=meta.type,
                    default=None if default is Ellipsis else default,
                    placeholder=meta.placeholder,
                    options=meta.options,
                    validation=meta.validation,
                    visible_when=meta.visible_when,
                    linked=meta.linked,
                )
            )
        return entries
