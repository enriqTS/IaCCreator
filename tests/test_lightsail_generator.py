"""Unit tests for LightsailGenerator.

Requirements: 16.1–16.5
"""

import pytest

from app.generators.lightsail_generator import LightsailGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_lightsail_instance(
    name: str = "my-lightsail",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Lightsail."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.LIGHTSAIL,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> LightsailGenerator:
    return LightsailGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestLightsailGeneratorMinimal:
    """Test LightsailGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_lightsail_instance(self, gen: LightsailGenerator):
        instance = _make_lightsail_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_lightsail_instance" in result

    def test_resource_tf_references_instance_name(self, gen: LightsailGenerator):
        instance = _make_lightsail_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.instance_name" in result

    def test_resource_tf_references_blueprint_id(self, gen: LightsailGenerator):
        instance = _make_lightsail_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.blueprint_id" in result

    def test_variables_tf_contains_required_variables(self, gen: LightsailGenerator):
        instance = _make_lightsail_instance()
        result = gen.generate_variables_tf(instance)
        assert "instance_name" in result
        assert "blueprint_id" in result
        assert "bundle_id" in result
        assert "availability_zone" in result

    def test_outputs_tf_contains_instance_arn(self, gen: LightsailGenerator):
        instance = _make_lightsail_instance()
        result = gen.generate_outputs_tf(instance)
        assert "instance_arn" in result

    def test_outputs_tf_contains_instance_name(self, gen: LightsailGenerator):
        instance = _make_lightsail_instance()
        result = gen.generate_outputs_tf(instance)
        assert "instance_name" in result
