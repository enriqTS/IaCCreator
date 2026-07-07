"""Unit tests for NeptuneGenerator.

Requirements: 32.1–32.5
"""

import pytest

from app.generators.neptune_generator import NeptuneGenerator
from app.models.input_models._general import ServiceType
from app.models.input_models.neptune_config import NeptuneConfig
from app.models.ir_models import ResourceInstanceIR


def _make_neptune_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Neptune."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.NEPTUNE,
        config=NeptuneConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> NeptuneGenerator:
    return NeptuneGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestNeptuneGeneratorMinimal:
    """Test NeptuneGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_neptune_cluster(self, gen: NeptuneGenerator):
        instance = _make_neptune_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_neptune_cluster" in result

    def test_variables_tf_contains_cluster_identifier(self, gen: NeptuneGenerator):
        instance = _make_neptune_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_identifier" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: NeptuneGenerator):
        instance = _make_neptune_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_cluster_endpoint(self, gen: NeptuneGenerator):
        instance = _make_neptune_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_endpoint" in result
