"""Redshift-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class RedshiftConfig(BaseServiceConfig):
    """Redshift-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.REDSHIFT] = ServiceType.REDSHIFT

    # Field order must match VARIABLE_SCHEMAS[ServiceType.REDSHIFT] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_identifier",
        "node_type",
        "master_username",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the Redshift cluster",
    )
    node_type: str | None = TerraformField(
        None,
        group="General",
        description="Node type for the Redshift cluster",
    )
    master_username: str | None = TerraformField(
        None,
        group="General",
        description="Master username for the Redshift cluster",
    )
