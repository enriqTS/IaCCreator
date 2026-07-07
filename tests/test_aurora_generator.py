"""Unit tests for AuroraGenerator.

Requirements: 26.1–26.7
"""

import pytest

from app.generators.aurora_generator import AuroraGenerator
from app.models.input_models._general import ServiceType
from app.models.input_models.aurora_config import AuroraConfig
from app.models.ir_models import ResourceInstanceIR


def _make_aurora_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Aurora."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.AURORA,
        config=AuroraConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> AuroraGenerator:
    return AuroraGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestAuroraGeneratorMinimal:
    """Test AuroraGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_rds_cluster(self, gen: AuroraGenerator):
        instance = _make_aurora_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_rds_cluster" in result

    def test_variables_tf_contains_cluster_identifier(self, gen: AuroraGenerator):
        instance = _make_aurora_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_identifier" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: AuroraGenerator):
        instance = _make_aurora_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_cluster_endpoint(self, gen: AuroraGenerator):
        instance = _make_aurora_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_endpoint" in result

    def test_resource_tf_no_engine_when_not_set(self, gen: AuroraGenerator):
        instance = _make_aurora_instance()
        result = gen.generate_resource_tf(instance)
        assert "engine" not in result

    def test_resource_tf_no_master_username_when_not_set(self, gen: AuroraGenerator):
        instance = _make_aurora_instance()
        result = gen.generate_resource_tf(instance)
        assert "master_username" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestAuroraGeneratorWithOptionalConfig:
    """Test AuroraGenerator with optional config fields set."""

    def test_resource_tf_includes_engine(self, gen: AuroraGenerator):
        instance = _make_aurora_instance(engine="aurora-mysql")
        result = gen.generate_resource_tf(instance)
        assert "engine" in result

    def test_variables_tf_includes_engine_variable(self, gen: AuroraGenerator):
        instance = _make_aurora_instance(engine="aurora-mysql")
        result = gen.generate_variables_tf(instance)
        assert "engine" in result

    def test_resource_tf_includes_master_username(self, gen: AuroraGenerator):
        instance = _make_aurora_instance(master_username="admin")
        result = gen.generate_resource_tf(instance)
        assert "master_username" in result

    def test_variables_tf_includes_master_username_variable(self, gen: AuroraGenerator):
        instance = _make_aurora_instance(master_username="admin")
        result = gen.generate_variables_tf(instance)
        assert "master_username" in result
