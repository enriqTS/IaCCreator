"""Unit tests for ElastiCacheGenerator.

Requirements: 30.1–30.8
"""

import pytest

from app.generators.elasticache_generator import ElastiCacheGenerator
from app.models.input_models._general import ServiceType
from app.models.input_models.elasticache_config import ElastiCacheConfig
from app.models.ir_models import ResourceInstanceIR


def _make_elasticache_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for ElastiCache."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.ELASTICACHE,
        config=ElastiCacheConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> ElastiCacheGenerator:
    return ElastiCacheGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestElastiCacheGeneratorMinimal:
    """Test ElastiCacheGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_elasticache_cluster(
        self, gen: ElastiCacheGenerator
    ):
        instance = _make_elasticache_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_elasticache_cluster" in result

    def test_variables_tf_contains_cluster_id(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_id" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_cache_nodes(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cache_nodes" in result

    def test_resource_tf_no_engine_when_not_set(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance()
        result = gen.generate_resource_tf(instance)
        assert "engine" not in result

    def test_resource_tf_no_node_type_when_not_set(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance()
        result = gen.generate_resource_tf(instance)
        assert "node_type" not in result

    def test_resource_tf_no_num_cache_nodes_when_not_set(
        self, gen: ElastiCacheGenerator
    ):
        instance = _make_elasticache_instance()
        result = gen.generate_resource_tf(instance)
        assert "num_cache_nodes" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestElastiCacheGeneratorWithOptionalConfig:
    """Test ElastiCacheGenerator with optional config fields set."""

    def test_resource_tf_includes_engine(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance(engine="redis")
        result = gen.generate_resource_tf(instance)
        assert "engine" in result

    def test_variables_tf_includes_engine_variable(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance(engine="redis")
        result = gen.generate_variables_tf(instance)
        assert "engine" in result

    def test_resource_tf_includes_node_type(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance(node_type="cache.t3.micro")
        result = gen.generate_resource_tf(instance)
        assert "node_type" in result

    def test_resource_tf_includes_num_cache_nodes(self, gen: ElastiCacheGenerator):
        instance = _make_elasticache_instance(num_cache_nodes=2)
        result = gen.generate_resource_tf(instance)
        assert "num_cache_nodes" in result
