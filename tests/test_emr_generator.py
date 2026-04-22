"""Unit tests for EMRGenerator.

Requirements: 6.1–6.7
"""

import pytest

from app.generators.emr_generator import EMRGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_emr_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for EMR."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.EMR,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> EMRGenerator:
    return EMRGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestEMRGeneratorMinimal:
    """Test EMRGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_emr_cluster(self, gen: EMRGenerator):
        instance = _make_emr_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_emr_cluster" in result

    def test_variables_tf_contains_cluster_name(self, gen: EMRGenerator):
        instance = _make_emr_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_name" in result

    def test_outputs_tf_contains_cluster_id(self, gen: EMRGenerator):
        instance = _make_emr_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_id" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: EMRGenerator):
        instance = _make_emr_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_resource_tf_no_release_label_when_not_set(self, gen: EMRGenerator):
        instance = _make_emr_instance()
        result = gen.generate_resource_tf(instance)
        assert "release_label" not in result

    def test_resource_tf_no_service_role_when_not_set(self, gen: EMRGenerator):
        instance = _make_emr_instance()
        result = gen.generate_resource_tf(instance)
        assert "service_role" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------

class TestEMRGeneratorWithOptionalConfig:
    """Test EMRGenerator with optional config fields set."""

    def test_resource_tf_includes_release_label(self, gen: EMRGenerator):
        instance = _make_emr_instance(emr_release_label="emr-6.10.0")
        result = gen.generate_resource_tf(instance)
        assert "release_label" in result

    def test_variables_tf_includes_release_label_variable(self, gen: EMRGenerator):
        instance = _make_emr_instance(emr_release_label="emr-6.10.0")
        result = gen.generate_variables_tf(instance)
        assert "release_label" in result

    def test_resource_tf_includes_service_role(self, gen: EMRGenerator):
        instance = _make_emr_instance(emr_service_role="arn:aws:iam::role/emr")
        result = gen.generate_resource_tf(instance)
        assert "service_role" in result

    def test_variables_tf_includes_service_role_variable(self, gen: EMRGenerator):
        instance = _make_emr_instance(emr_service_role="arn:aws:iam::role/emr")
        result = gen.generate_variables_tf(instance)
        assert "service_role" in result
