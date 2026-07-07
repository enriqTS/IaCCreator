"""Shared base models and common fields for all service configurations."""

from __future__ import annotations

from typing import get_type_hints

from pydantic import BaseModel

from app.models.input_models._connections import ConnectionInput
from app.models.input_models._metadata import (
    VariableSchemaEntry,
    _infer_tf_type,
    get_terraform_meta,
)


class BaseServiceConfig(BaseModel):
    """Shared base for all service configs. Icon-only services use this directly.

    Subclasses annotate fields with `TerraformField(...)` to declare Terraform
    variable metadata. The `get_variable_schema()` classmethod introspects these
    annotations to produce the schema served to the frontend.
    """

    tags: dict[str, str] | None = None
    description: str | None = None
    environment_variables: dict[str, str] | None = None

    @classmethod
    def get_variable_schema(cls) -> list[VariableSchemaEntry]:
        """Introspect this model's fields and return Terraform variable schema entries.

        Only fields annotated with `TerraformField(...)` are included in the output.
        Fields without Terraform metadata (e.g., `service_type` discriminator) are skipped.

        Returns a list of `VariableSchemaEntry` matching the format served by
        `/api/variable-schemas`.
        """
        entries: list[VariableSchemaEntry] = []
        hints = get_type_hints(cls)

        for field_name, field_info in cls.model_fields.items():
            meta = get_terraform_meta(field_info)
            if meta is None:
                # Field not annotated with TerraformField — skip
                continue

            # Determine the Terraform type
            tf_type = meta.tf_type
            if tf_type is None:
                annotation = hints.get(field_name, str)
                tf_type = _infer_tf_type(annotation)

            # Resolve default value
            default = field_info.default
            if default is ...:
                default = None

            # Build schema entry
            entry = VariableSchemaEntry(
                name=field_name,
                type=tf_type,
                description=field_info.description or "",
                default=default if not isinstance(default, (dict, list)) else None,
                group=meta.group,
                options=meta.options,
                validation=meta.validation,
                visible_when=meta.visible_when,
            )
            entries.append(entry)

        return entries

    @classmethod
    def get_connections_schema(cls) -> list[ConnectionInput]:
        """Return connection-derived inputs for this service.

        Override in subclasses that receive inputs from service connections.
        Default implementation returns an empty list.
        """
        return []

    @classmethod
    def has_terraform_schema(cls) -> bool:
        """Return True if this config model has any TerraformField-annotated fields.

        Used to determine whether to use model introspection or fall back to
        the legacy VARIABLE_SCHEMAS dict during the migration.
        """
        for field_info in cls.model_fields.values():
            if get_terraform_meta(field_info) is not None:
                return True
        return False
