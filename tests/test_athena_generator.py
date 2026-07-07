"""Unit tests for AthenaGenerator.

Requirements: 2.1–2.5
"""

import pytest

from app.generators.athena_generator import AthenaGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_athena_instance(
    name: str = "my-workgroup",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Athena."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.ATHENA,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> AthenaGenerator:
    return AthenaGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestAthenaGeneratorMinimal:
    """Test AthenaGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_athena_workgroup(self, gen: AthenaGenerator):
        instance = _make_athena_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_athena_workgroup" in result

    def test_variables_tf_contains_workgroup_name(self, gen: AthenaGenerator):
        instance = _make_athena_instance()
        result = gen.generate_variables_tf(instance)
        assert "workgroup_name" in result

    def test_outputs_tf_contains_workgroup_arn(self, gen: AthenaGenerator):
        instance = _make_athena_instance()
        result = gen.generate_outputs_tf(instance)
        assert "workgroup_arn" in result

    def test_outputs_tf_contains_workgroup_name(self, gen: AthenaGenerator):
        instance = _make_athena_instance()
        result = gen.generate_outputs_tf(instance)
        assert "workgroup_name" in result
