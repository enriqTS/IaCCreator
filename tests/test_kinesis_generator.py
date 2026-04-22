"""Unit tests for KinesisGenerator.

Requirements: 10.1–10.6
"""

import pytest

from app.generators.kinesis_generator import KinesisGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_kinesis_instance(
    name: str = "my-stream",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Kinesis."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.KINESIS,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> KinesisGenerator:
    return KinesisGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestKinesisGeneratorMinimal:
    """Test KinesisGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_kinesis_stream(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_kinesis_stream" in result

    def test_variables_tf_contains_stream_name(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance()
        result = gen.generate_variables_tf(instance)
        assert "stream_name" in result

    def test_outputs_tf_contains_stream_arn(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance()
        result = gen.generate_outputs_tf(instance)
        assert "stream_arn" in result

    def test_outputs_tf_contains_stream_name(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance()
        result = gen.generate_outputs_tf(instance)
        assert "stream_name" in result

    def test_resource_tf_no_shard_count_when_not_set(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance()
        result = gen.generate_resource_tf(instance)
        assert "shard_count" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------

class TestKinesisGeneratorWithOptionalConfig:
    """Test KinesisGenerator with optional config fields set."""

    def test_resource_tf_includes_shard_count(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance(kinesis_shard_count=4)
        result = gen.generate_resource_tf(instance)
        assert "shard_count" in result

    def test_variables_tf_includes_shard_count_variable(self, gen: KinesisGenerator):
        instance = _make_kinesis_instance(kinesis_shard_count=4)
        result = gen.generate_variables_tf(instance)
        assert "shard_count" in result
