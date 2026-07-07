"""Glue-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class GlueConfig(BaseServiceConfig):
    """Glue-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.GLUE] = ServiceType.GLUE

    # Field order must match VARIABLE_SCHEMAS[ServiceType.GLUE] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = ("database_name",)

    # ── General ───────────────────────────────────────────────────────────
    database_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Glue catalog database",
    )
