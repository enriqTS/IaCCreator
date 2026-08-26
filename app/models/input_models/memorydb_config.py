"""Amazon MemoryDB cluster configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class MemoryDbConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MEMORYDB] = ServiceType.MEMORYDB
    cluster_name: str = TerraformField(
        "memorydb-cluster", description="MemoryDB cluster name"
    )
    node_type: str = TerraformField("db.t4g.small", description="MemoryDB node type")
    num_shards: int = TerraformField(
        1, description="Number of shards", validation=ValidationRule(min=1, max=500)
    )
    num_replicas_per_shard: int = TerraformField(
        1, description="Replicas per shard", validation=ValidationRule(min=0, max=5)
    )
    acl_name: str = TerraformField("open-access", description="MemoryDB ACL name")
    subnet_ids: list[str] = TerraformField(
        [], description="Subnets for the MemoryDB subnet group"
    )
    security_group_ids: list[str] = TerraformField(
        [], description="VPC security groups for the cluster"
    )
    tls_enabled: bool = TerraformField(True, description="Encrypt traffic in transit")
    snapshot_retention_limit: int = TerraformField(
        0,
        description="Daily snapshot retention in days",
        validation=ValidationRule(min=0, max=35),
    )
    maintenance_window: str | None = TerraformField(
        None, description="Weekly maintenance window"
    )
