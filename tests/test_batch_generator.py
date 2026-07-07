"""Unit tests for BatchGenerator.

Requirements: 12.1–12.6
"""

import pytest

from app.generators.batch_generator import BatchGenerator
from app.models.input_models import ServiceType
from app.models.input_models.batch_config import BatchConfig
from app.models.ir_models import ResourceInstanceIR


def _make_batch_instance(
    name: str = "my-batch",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Batch."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.BATCH,
        config=BatchConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> BatchGenerator:
    return BatchGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestBatchGeneratorMinimal:
    """Test BatchGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_batch_compute_environment(self, gen: BatchGenerator):
        instance = _make_batch_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_batch_compute_environment" in result

    def test_variables_tf_contains_required_variables(self, gen: BatchGenerator):
        instance = _make_batch_instance()
        result = gen.generate_variables_tf(instance)
        assert "compute_environment_name" in result
        assert "service_role_arn" in result

    def test_outputs_tf_contains_compute_environment_arn(self, gen: BatchGenerator):
        instance = _make_batch_instance()
        result = gen.generate_outputs_tf(instance)
        assert "compute_environment_arn" in result

    def test_outputs_tf_contains_compute_environment_name(self, gen: BatchGenerator):
        instance = _make_batch_instance()
        result = gen.generate_outputs_tf(instance)
        assert "compute_environment_name" in result

    def test_resource_tf_no_type_when_not_set(self, gen: BatchGenerator):
        instance = _make_batch_instance()
        result = gen.generate_resource_tf(instance)
        # "type" is a common word; check for the variable reference instead
        assert "batch_compute_environment_type" not in result

    def test_resource_tf_no_compute_resources_when_not_set(self, gen: BatchGenerator):
        instance = _make_batch_instance()
        result = gen.generate_resource_tf(instance)
        assert "compute_resources" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestBatchGeneratorWithOptionalConfig:
    """Test BatchGenerator with optional config fields set."""

    def test_resource_tf_includes_type(self, gen: BatchGenerator):
        instance = _make_batch_instance(batch_compute_environment_type="MANAGED")
        result = gen.generate_resource_tf(instance)
        assert "type" in result

    def test_resource_tf_includes_max_vcpus(self, gen: BatchGenerator):
        instance = _make_batch_instance(batch_max_vcpus=256)
        result = gen.generate_resource_tf(instance)
        assert "max_vcpus" in result

    def test_variables_tf_includes_type_variable(self, gen: BatchGenerator):
        instance = _make_batch_instance(batch_compute_environment_type="MANAGED")
        result = gen.generate_variables_tf(instance)
        assert "batch_compute_environment_type" in result

    def test_variables_tf_includes_max_vcpus_variable(self, gen: BatchGenerator):
        instance = _make_batch_instance(batch_max_vcpus=256)
        result = gen.generate_variables_tf(instance)
        assert "batch_max_vcpus" in result
