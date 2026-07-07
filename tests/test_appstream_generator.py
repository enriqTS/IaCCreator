"""Unit tests for AppStreamGenerator.

Requirements: 46.1–46.6
"""

import pytest

from app.generators.appstream_generator import AppStreamGenerator
from app.models.input_models import ServiceType
from app.models.input_models.appstream_config import AppStreamConfig
from app.models.ir_models import ResourceInstanceIR


def _make_appstream_instance(
    name: str = "my-fleet",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for AppStream."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.APPSTREAM,
        config=AppStreamConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> AppStreamGenerator:
    return AppStreamGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestAppStreamGeneratorMinimal:
    """Test AppStreamGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_appstream_fleet(self, gen: AppStreamGenerator):
        instance = _make_appstream_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_appstream_fleet" in result

    def test_variables_tf_contains_fleet_name(self, gen: AppStreamGenerator):
        instance = _make_appstream_instance()
        result = gen.generate_variables_tf(instance)
        assert "fleet_name" in result

    def test_outputs_tf_contains_fleet_arn(self, gen: AppStreamGenerator):
        instance = _make_appstream_instance()
        result = gen.generate_outputs_tf(instance)
        assert "fleet_arn" in result

    def test_outputs_tf_contains_fleet_name(self, gen: AppStreamGenerator):
        instance = _make_appstream_instance()
        result = gen.generate_outputs_tf(instance)
        assert "fleet_name" in result

    def test_resource_tf_no_instance_type_when_not_set(self, gen: AppStreamGenerator):
        instance = _make_appstream_instance()
        result = gen.generate_resource_tf(instance)
        assert "instance_type" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestAppStreamGeneratorWithOptionalConfig:
    """Test AppStreamGenerator with optional config fields set."""

    def test_resource_tf_includes_instance_type(self, gen: AppStreamGenerator):
        instance = _make_appstream_instance(instance_type="stream.standard.medium")
        result = gen.generate_resource_tf(instance)
        assert "instance_type" in result

    def test_variables_tf_includes_instance_type_variable(
        self, gen: AppStreamGenerator
    ):
        instance = _make_appstream_instance(instance_type="stream.standard.medium")
        result = gen.generate_variables_tf(instance)
        assert "instance_type" in result
