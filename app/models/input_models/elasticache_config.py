"""ElastiCache-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ElastiCacheConfig(BaseServiceConfig):
    """ElastiCache-specific configuration."""

    service_type: Literal[ServiceType.ELASTICACHE] = ServiceType.ELASTICACHE

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_id",
        "engine",
        "node_type",
        "num_cache_nodes",
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
