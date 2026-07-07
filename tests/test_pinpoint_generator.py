"""Unit tests for PinpointGenerator.

Requirements: 24.1–24.5
"""

import pytest

from app.generators.pinpoint_generator import PinpointGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_pinpoint_instance(
    name: str = "my-app",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Pinpoint."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.PINPOINT,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> PinpointGenerator:
    return PinpointGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestPinpointGeneratorMinimal:
    """Test PinpointGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_pinpoint_app(self, gen: PinpointGenerator):
        instance = _make_pinpoint_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_pinpoint_app" in result

    def test_variables_tf_contains_app_name(self, gen: PinpointGenerator):
        instance = _make_pinpoint_instance()
        result = gen.generate_variables_tf(instance)
        assert "app_name" in result

    def test_outputs_tf_contains_application_id(self, gen: PinpointGenerator):
        instance = _make_pinpoint_instance()
        result = gen.generate_outputs_tf(instance)
        assert "application_id" in result

    def test_outputs_tf_contains_app_arn(self, gen: PinpointGenerator):
        instance = _make_pinpoint_instance()
        result = gen.generate_outputs_tf(instance)
        assert "app_arn" in result
