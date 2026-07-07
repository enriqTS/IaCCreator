"""Athena-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AthenaConfig(BaseServiceConfig):
    """Athena-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.ATHENA] = ServiceType.ATHENA

    # Field order must match VARIABLE_SCHEMAS[ServiceType.ATHENA] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = ("workgroup_name",)

    # ── General ───────────────────────────────────────────────────────────
    workgroup_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Athena workgroup",
    )
