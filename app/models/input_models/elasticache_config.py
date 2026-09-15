"""ElastiCache-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ElastiCacheConfig(BaseServiceConfig):
    """ElastiCache-specific configuration."""

    service_type: Literal[ServiceType.ELASTICACHE] = ServiceType.ELASTICACHE

    _client_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_id",
        "engine",
        "node_type",
        "num_cache_nodes",
        "parameter_group_name",
        "engine_version",
        "subnet_group_name",
        "security_group_ids",
    )

    parameter_group_name: str | None = TerraformField(
        None,
        description="Existing parameter group compatible with the cache engine version",
    )
    engine_version: str | None = TerraformField(
        None, description="Optional cache engine version"
    )
    subnet_group_name: str | None = TerraformField(
        None, description="Existing cache subnet group"
    )
    security_group_ids: list[str] = TerraformField(
        [], description="Cache VPC security groups"
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_id: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the ElastiCache cluster",
    )
    engine: str | None = TerraformField(
        None,
        group="General",
        description="Cache engine type",
    )
    node_type: str | None = TerraformField(
        None,
        group="General",
        description="ElastiCache node type",
    )
    num_cache_nodes: int | None = TerraformField(
        None,
        group="General",
        description="Number of cache nodes in the cluster",
    )
