"""Terraform generator for Amazon MemoryDB clusters."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.memorydb_config import MemoryDbConfig
from app.models.ir_models import ResourceInstanceIR


class MemoryDbGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, MemoryDbConfig)
        parts = []
        if config.subnet_ids:
            parts.append(
                self._r.render_resource(
                    "aws_memorydb_subnet_group",
                    instance.name,
                    {
                        "name": f"{instance.name.replace('_', '-')}-subnets",
                        "subnet_ids": Expr("var.subnet_ids"),
                    },
                )
            )
        attrs = {
            "name": Expr("var.cluster_name"),
            "node_type": Expr("var.node_type"),
            "num_shards": Expr("var.num_shards"),
            "num_replicas_per_shard": Expr("var.num_replicas_per_shard"),
            "acl_name": Expr("var.acl_name"),
            "security_group_ids": Expr("var.security_group_ids"),
            "tls_enabled": Expr("var.tls_enabled"),
            "snapshot_retention_limit": Expr("var.snapshot_retention_limit"),
        }
        if config.subnet_ids:
            attrs["subnet_group_name"] = Expr(
                f"aws_memorydb_subnet_group.{instance.name}.name"
            )
        if config.maintenance_window is not None:
            attrs["maintenance_window"] = Expr("var.maintenance_window")
        parts.append(
            self._r.render_resource("aws_memorydb_cluster", instance.name, attrs)
        )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, MemoryDbConfig)
        fields = [
            ("cluster_name", "string", "MemoryDB cluster name"),
            ("node_type", "string", "MemoryDB node type"),
            ("num_shards", "number", "Number of shards"),
            ("num_replicas_per_shard", "number", "Replicas per shard"),
            ("acl_name", "string", "MemoryDB ACL name"),
            ("subnet_ids", "list(string)", "MemoryDB subnet IDs"),
            ("security_group_ids", "list(string)", "MemoryDB security group IDs"),
            ("tls_enabled", "bool", "Encrypt traffic in transit"),
            ("snapshot_retention_limit", "number", "Snapshot retention in days"),
        ]
        if config.maintenance_window is not None:
            fields.append(("maintenance_window", "string", "Weekly maintenance window"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_memorydb_cluster.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "cluster_arn", f"{ref}.arn", "MemoryDB cluster ARN"
                ),
                self._r.render_output(
                    "cluster_endpoint",
                    f"{ref}.cluster_endpoint",
                    "MemoryDB cluster endpoint",
                ),
            ]
        )
