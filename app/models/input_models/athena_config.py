"""Athena-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AthenaConfig(BaseServiceConfig):
    """Athena-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.ATHENA] = ServiceType.ATHENA

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "workgroup_name",
        "output_location",
        "enforce_workgroup_configuration",
    )

    # ── General ───────────────────────────────────────────────────────────
    workgroup_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Athena workgroup",
    )

    output_location: str | None = TerraformField(
        None, group="Results", description="External S3 query result location"
    )
    enforce_workgroup_configuration: bool = TerraformField(
        True,
        group="Results",
        description="Enforce the workgroup result location over client settings",
    )
