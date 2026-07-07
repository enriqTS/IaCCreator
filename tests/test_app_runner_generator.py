"""Unit tests for AppRunnerGenerator.

Requirements: 10.1–10.5
"""

import pytest

from app.generators.app_runner_generator import AppRunnerGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_app_runner_instance(
    name: str = "my-service",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for App Runner."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.APP_RUNNER,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> AppRunnerGenerator:
    return AppRunnerGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestAppRunnerGeneratorMinimal:
    """Test AppRunnerGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_apprunner_service(self, gen: AppRunnerGenerator):
        instance = _make_app_runner_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_apprunner_service" in result

    def test_resource_tf_contains_source_configuration(self, gen: AppRunnerGenerator):
        instance = _make_app_runner_instance()
        result = gen.generate_resource_tf(instance)
        assert "source_configuration" in result

    def test_resource_tf_contains_image_repository(self, gen: AppRunnerGenerator):
        instance = _make_app_runner_instance()
        result = gen.generate_resource_tf(instance)
        assert "image_repository" in result

    def test_variables_tf_contains_required_variables(self, gen: AppRunnerGenerator):
        instance = _make_app_runner_instance()
        result = gen.generate_variables_tf(instance)
        assert "service_name" in result
        assert "image_identifier" in result

    def test_outputs_tf_contains_service_arn(self, gen: AppRunnerGenerator):
        instance = _make_app_runner_instance()
        result = gen.generate_outputs_tf(instance)
        assert "service_arn" in result

    def test_outputs_tf_contains_service_url(self, gen: AppRunnerGenerator):
        instance = _make_app_runner_instance()
        result = gen.generate_outputs_tf(instance)
        assert "service_url" in result
