"""Unit tests for TimestreamGenerator.

Requirements: 36.1–36.5
"""

import pytest

from app.generators.timestream_generator import TimestreamGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_timestream_instance(
    name: str = "my-database",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Timestream."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.TIMESTREAM,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> TimestreamGenerator:
    return TimestreamGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestTimestreamGeneratorMinimal:
    """Test TimestreamGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_timestreamwrite_database(self, gen: TimestreamGenerator):
        instance = _make_timestream_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_timestreamwrite_database" in result

    def test_variables_tf_contains_database_name(self, gen: TimestreamGenerator):
        instance = _make_timestream_instance()
        result = gen.generate_variables_tf(instance)
        assert "database_name" in result

    def test_outputs_tf_contains_database_arn(self, gen: TimestreamGenerator):
        instance = _make_timestream_instance()
        result = gen.generate_outputs_tf(instance)
        assert "database_arn" in result

    def test_outputs_tf_contains_database_name(self, gen: TimestreamGenerator):
        instance = _make_timestream_instance()
        result = gen.generate_outputs_tf(instance)
        assert "database_name" in result
