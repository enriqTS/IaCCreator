"""EMR-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class EmrConfig(BaseServiceConfig):
    """EMR-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.EMR] = ServiceType.EMR

    # Field order must match VARIABLE_SCHEMAS[ServiceType.EMR] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_name",
        "release_label",
        "service_role",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the EMR cluster",
    )
    release_label: str | None = TerraformField(
        None,
        group="General",
        description="EMR release label",
    )
    service_role: str | None = TerraformField(
        None,
        group="General",
        description="IAM service role for the EMR cluster",
    )
