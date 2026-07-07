"""ElastiCache-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class ElastiCacheConfig(BaseServiceConfig):
    """ElastiCache-specific configuration."""

    service_type: Literal[ServiceType.ELASTICACHE] = ServiceType.ELASTICACHE
    elasticache_engine: Optional[str] = None
    elasticache_node_type: Optional[str] = None
    elasticache_num_cache_nodes: Optional[int] = None
