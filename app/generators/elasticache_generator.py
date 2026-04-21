"""ElastiCache service generator — produces HCL for aws_elasticache_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class ElastiCacheGenerator:
    """Generates Terraform files for ElastiCache clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_elasticache_cluster resource."""
        attrs: dict = {"cluster_id": "var.cluster_id"}
        if instance.config.elasticache_engine is not None:
            attrs["engine"] = "var.engine"
        if instance.config.elasticache_node_type is not None:
            attrs["node_type"] = "var.node_type"
        if instance.config.elasticache_num_cache_nodes is not None:
            attrs["num_cache_nodes"] = "var.num_cache_nodes"

        return self._r.render_resource("aws_elasticache_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an ElastiCache cluster."""
        parts = [
            self._r.render_variable("cluster_id", "string", "ID of the ElastiCache cluster"),
        ]
        if instance.config.elasticache_engine is not None:
            parts.append(self._r.render_variable(
                "engine", "string", "Cache engine for the ElastiCache cluster",
                default=instance.config.elasticache_engine,
            ))
        if instance.config.elasticache_node_type is not None:
            parts.append(self._r.render_variable(
                "node_type", "string", "Node type for the ElastiCache cluster",
                default=instance.config.elasticache_node_type,
            ))
        if instance.config.elasticache_num_cache_nodes is not None:
            parts.append(self._r.render_variable(
                "num_cache_nodes", "number", "Number of cache nodes in the ElastiCache cluster",
                default=instance.config.elasticache_num_cache_nodes,
            ))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an ElastiCache cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_elasticache_cluster.{instance.name}.arn",
                "ARN of the ElastiCache cluster",
            ),
            self._r.render_output(
                "cache_nodes",
                f"aws_elasticache_cluster.{instance.name}.cache_nodes",
                "Cache nodes of the ElastiCache cluster",
            ),
        ]
        return "\n".join(parts)
