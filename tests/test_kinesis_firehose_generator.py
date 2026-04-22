"""Unit tests for KinesisFirehoseGenerator.

Requirements: 12.1–12.6
"""

import pytest

from app.generators.kinesis_firehose_generator import KinesisFirehoseGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_firehose_instance(
    name: str = "my-stream",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Kinesis Firehose."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.KINESIS_FIREHOSE,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> KinesisFirehoseGenerator:
    return KinesisFirehoseGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestKinesisFirehoseGeneratorMinimal:
    """Test KinesisFirehoseGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_kinesis_firehose_delivery_stream(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_kinesis_firehose_delivery_stream" in result

    def test_variables_tf_contains_stream_name(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance()
        result = gen.generate_variables_tf(instance)
        assert "stream_name" in result

    def test_outputs_tf_contains_delivery_stream_arn(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance()
        result = gen.generate_outputs_tf(instance)
        assert "delivery_stream_arn" in result

    def test_outputs_tf_contains_delivery_stream_name(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance()
        result = gen.generate_outputs_tf(instance)
        assert "delivery_stream_name" in result

    def test_resource_tf_no_destination_when_not_set(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance()
        result = gen.generate_resource_tf(instance)
        assert "destination" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------

class TestKinesisFirehoseGeneratorWithOptionalConfig:
    """Test KinesisFirehoseGenerator with optional config fields set."""

    def test_resource_tf_includes_destination(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance(firehose_destination="s3")
        result = gen.generate_resource_tf(instance)
        assert "destination" in result

    def test_variables_tf_includes_destination_variable(self, gen: KinesisFirehoseGenerator):
        instance = _make_firehose_instance(firehose_destination="s3")
        result = gen.generate_variables_tf(instance)
        assert "destination" in result
