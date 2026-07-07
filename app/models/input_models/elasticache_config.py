"""ElastiCache-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class ElastiCacheConfig(BaseServiceConfig):
    """ElastiCache-specific configuration."""

    service_type: Literal[ServiceType.ELASTICACHE] = ServiceType.ELASTICACHE
    elasticache_engine: str | None = None
    elasticache_node_type: str | None = None
    elasticache_num_cache_nodes: int | None = None
