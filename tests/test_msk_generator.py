"""Unit tests for MSKGenerator.

Requirements: 14.1–14.7
"""

import pytest

from app.generators.msk_generator import MSKGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_msk_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for MSK."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.MSK,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> MSKGenerator:
    return MSKGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestMSKGeneratorMinimal:
    """Test MSKGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_msk_cluster(self, gen: MSKGenerator):
        instance = _make_msk_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_msk_cluster" in result

    def test_variables_tf_contains_cluster_name(self, gen: MSKGenerator):
        instance = _make_msk_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_name" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: MSKGenerator):
        instance = _make_msk_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_bootstrap_brokers(self, gen: MSKGenerator):
        instance = _make_msk_instance()
        result = gen.generate_outputs_tf(instance)
        assert "bootstrap_brokers" in result

    def test_resource_tf_no_kafka_version_when_not_set(self, gen: MSKGenerator):
        instance = _make_msk_instance()
        result = gen.generate_resource_tf(instance)
        assert "kafka_version" not in result

    def test_resource_tf_no_number_of_broker_nodes_when_not_set(
        self, gen: MSKGenerator
    ):
        instance = _make_msk_instance()
        result = gen.generate_resource_tf(instance)
        assert "number_of_broker_nodes" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestMSKGeneratorWithOptionalConfig:
    """Test MSKGenerator with optional config fields set."""

    def test_resource_tf_includes_kafka_version(self, gen: MSKGenerator):
        instance = _make_msk_instance(msk_kafka_version="3.5.1")
        result = gen.generate_resource_tf(instance)
        assert "kafka_version" in result

    def test_variables_tf_includes_kafka_version_variable(self, gen: MSKGenerator):
        instance = _make_msk_instance(msk_kafka_version="3.5.1")
        result = gen.generate_variables_tf(instance)
        assert "kafka_version" in result

    def test_resource_tf_includes_number_of_broker_nodes(self, gen: MSKGenerator):
        instance = _make_msk_instance(msk_number_of_broker_nodes=3)
        result = gen.generate_resource_tf(instance)
        assert "number_of_broker_nodes" in result

    def test_variables_tf_includes_number_of_broker_nodes_variable(
        self, gen: MSKGenerator
    ):
        instance = _make_msk_instance(msk_number_of_broker_nodes=3)
        result = gen.generate_variables_tf(instance)
        assert "number_of_broker_nodes" in result
