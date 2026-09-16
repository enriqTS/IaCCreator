"""ElastiCache-specific configuration model."""

import re
from typing import ClassVar, Literal

from pydantic import PrivateAttr, model_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField

MEMCACHED_TLS_VERSION_PATTERN = r"^(1\.6\.(1[2-9]|[2-9][0-9]|[1-9][0-9]{2,})|1\.([7-9]|[1-9][0-9]+)\.[0-9]+|([2-9]|[1-9][0-9]+)\.[0-9]+\.[0-9]+)$"
MEMCACHED_TLS_UNSUPPORTED_NODES = r"^cache\.(m1|m2|m3|r3|t2)\."


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
        "transit_encryption_enabled",
        "subnet_group_name",
        "security_group_ids",
    )

    transit_encryption_enabled: bool = TerraformField(
        False,
        description="Enable TLS when creating a Memcached cluster; requires engine 1.6.12+, supported VPC nodes, and an existing subnet group",
    )

    @model_validator(mode="after")
    def validate_tls(self):
        if not self.transit_encryption_enabled:
            return self
        if self.engine != "memcached" or not re.fullmatch(
            MEMCACHED_TLS_VERSION_PATTERN, self.engine_version or ""
        ):
            raise ValueError("Standalone cache TLS requires Memcached 1.6.12 or newer")
        if not self.subnet_group_name or not self.subnet_group_name.strip():
            raise ValueError("Memcached TLS requires an existing VPC subnet group")
        if not re.fullmatch(
            r"cache\.[a-z][a-z0-9]*\.[a-z0-9]+", self.node_type or ""
        ) or re.match(MEMCACHED_TLS_UNSUPPORTED_NODES, self.node_type):
            raise ValueError(
                "Memcached TLS requires a supported node type; M1, M2, M3, R3, and T2 are unsupported"
            )
        return self

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
