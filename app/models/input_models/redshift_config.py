"""Redshift-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class RedshiftConfig(BaseServiceConfig):
    """Redshift-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.REDSHIFT] = ServiceType.REDSHIFT
    _grafana_query_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_identifier",
        "node_type",
        "number_of_nodes",
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
    number_of_nodes: int | None = TerraformField(
        None,
        group="General",
        description="Cluster node count; omitted uses the provider's single-node default",
        validation=ValidationRule(min=1, max=128),
    )
