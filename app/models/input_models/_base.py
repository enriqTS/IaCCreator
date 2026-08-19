"""Shared base models and common fields for all service configurations."""

from __future__ import annotations

from typing import ClassVar, get_type_hints

from pydantic import BaseModel

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
    is_layer: bool = False

    # Services that assume an AWS role declare it here so connections can grant to them
    owns_execution_role: ClassVar[bool] = False
    execution_role_principal: ClassVar[str | None] = None

    # Subclasses may define _schema_field_order as a ClassVar tuple of field names
    # to control the order of entries returned by get_variable_schema(). This is
    # needed when inherited fields (e.g. tags) must appear in a specific
    # position to match the order the editor renders them in.
    _schema_field_order: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def get_variable_schema(cls) -> list[VariableSchemaEntry]:
        """Introspect this model's fields and return Terraform variable schema entries.

        Only fields annotated with `TerraformField(...)` are included in the output.
        Fields without Terraform metadata (e.g., `service_type` discriminator) are skipped.

        If the subclass defines `_schema_field_order`, entries are returned in that
        order. Otherwise, entries follow `model_fields` iteration order.

        Returns a list of `VariableSchemaEntry` matching the format served by
        `/api/variable-schemas`.
        """
        entries: list[VariableSchemaEntry] = []
        hints = get_type_hints(cls)

        # Determine iteration order
        field_order: tuple[str, ...] | None = getattr(cls, "_schema_field_order", None)
        if field_order is not None:
            field_items = [
                (name, cls.model_fields[name])
                for name in field_order
                if name in cls.model_fields
            ]
        else:
            field_items = list(cls.model_fields.items())

        for field_name, field_info in field_items:
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
                required=field_info.is_required(),
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
    def execution_role_base_statements(cls, instance_name: str) -> list[dict]:
        """Statements the role always needs, before any connection grants."""
        return []

    @classmethod
    def has_terraform_schema(cls) -> bool:
        """Return True if this config model has any TerraformField-annotated fields.

        Icon-only services have no annotated fields and expose no variables.
        """
        for field_info in cls.model_fields.values():
            if get_terraform_meta(field_info) is not None:
                return True
        return False
