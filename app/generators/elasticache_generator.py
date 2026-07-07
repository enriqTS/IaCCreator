"""ElastiCache service generator — produces HCL for aws_elasticache_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.elasticache_config import ElastiCacheConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> ElastiCacheConfig:
    """Resolve typed ElastiCacheConfig from the instance."""
    if isinstance(instance.config, ElastiCacheConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class ElastiCacheGenerator:
    """Generates Terraform files for ElastiCache clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_elasticache_cluster resource."""
        config = _resolve_config(instance)
        attrs: dict = {"cluster_id": "var.cluster_id"}
        if config.engine is not None:
            attrs["engine"] = "var.engine"
        if config.node_type is not None:
            attrs["node_type"] = "var.node_type"
        if config.num_cache_nodes is not None:
            attrs["num_cache_nodes"] = "var.num_cache_nodes"

        return self._r.render_resource("aws_elasticache_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an ElastiCache cluster."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "cluster_id", "string", "Identifier for the ElastiCache cluster"
            ),
        ]
        if config.engine is not None:
            parts.append(
                self._r.render_variable(
                    "engine",
                    "string",
                    "Cache engine type",
                    default=config.engine,
                )
            )
        if config.node_type is not None:
            parts.append(
                self._r.render_variable(
                    "node_type",
                    "string",
                    "ElastiCache node type",
                    default=config.node_type,
                )
            )
        if config.num_cache_nodes is not None:
            parts.append(
                self._r.render_variable(
                    "num_cache_nodes",
                    "number",
                    "Number of cache nodes in the cluster",
                    default=config.num_cache_nodes,
                )
            )
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
