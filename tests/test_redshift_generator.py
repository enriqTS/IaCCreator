"""Unit tests for RedshiftGenerator.

Requirements: 18.1–18.7
"""

import pytest

from app.generators.redshift_generator import RedshiftGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_redshift_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Redshift."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.REDSHIFT,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> RedshiftGenerator:
    return RedshiftGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestRedshiftGeneratorMinimal:
    """Test RedshiftGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_redshift_cluster(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_redshift_cluster" in result

    def test_variables_tf_contains_cluster_identifier(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_identifier" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_cluster_endpoint(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_endpoint" in result

    def test_resource_tf_no_node_type_when_not_set(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance()
        result = gen.generate_resource_tf(instance)
        assert "node_type" not in result

    def test_resource_tf_no_master_username_when_not_set(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance()
        result = gen.generate_resource_tf(instance)
        assert "master_username" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestRedshiftGeneratorWithOptionalConfig:
    """Test RedshiftGenerator with optional config fields set."""

    def test_resource_tf_includes_node_type(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance(redshift_node_type="dc2.large")
        result = gen.generate_resource_tf(instance)
        assert "node_type" in result

    def test_variables_tf_includes_node_type_variable(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance(redshift_node_type="dc2.large")
        result = gen.generate_variables_tf(instance)
        assert "node_type" in result

    def test_resource_tf_includes_master_username(self, gen: RedshiftGenerator):
        instance = _make_redshift_instance(redshift_master_username="admin")
        result = gen.generate_resource_tf(instance)
        assert "master_username" in result

    def test_variables_tf_includes_master_username_variable(
        self, gen: RedshiftGenerator
    ):
        instance = _make_redshift_instance(redshift_master_username="admin")
        result = gen.generate_variables_tf(instance)
        assert "master_username" in result
