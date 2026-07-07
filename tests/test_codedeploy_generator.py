"""Unit tests for CodeDeployGenerator.

Requirements: 42.1–42.6
"""

import pytest

from app.generators.codedeploy_generator import CodeDeployGenerator
from app.models.input_models import ServiceType
from app.models.input_models.codedeploy_config import CodeDeployConfig
from app.models.ir_models import ResourceInstanceIR


def _make_codedeploy_instance(
    name: str = "my-app",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for CodeDeploy."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.CODEDEPLOY,
        config=CodeDeployConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> CodeDeployGenerator:
    return CodeDeployGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestCodeDeployGeneratorMinimal:
    """Test CodeDeployGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_codedeploy_app(self, gen: CodeDeployGenerator):
        instance = _make_codedeploy_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_codedeploy_app" in result

    def test_variables_tf_contains_app_name(self, gen: CodeDeployGenerator):
        instance = _make_codedeploy_instance()
        result = gen.generate_variables_tf(instance)
        assert "app_name" in result

    def test_outputs_tf_contains_app_id(self, gen: CodeDeployGenerator):
        instance = _make_codedeploy_instance()
        result = gen.generate_outputs_tf(instance)
        assert "app_id" in result

    def test_outputs_tf_contains_app_name(self, gen: CodeDeployGenerator):
        instance = _make_codedeploy_instance()
        result = gen.generate_outputs_tf(instance)
        assert "app_name" in result

    def test_resource_tf_no_compute_platform_when_not_set(
        self, gen: CodeDeployGenerator
    ):
        instance = _make_codedeploy_instance()
        result = gen.generate_resource_tf(instance)
        assert "compute_platform" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestCodeDeployGeneratorWithOptionalConfig:
    """Test CodeDeployGenerator with optional config fields set."""

    def test_resource_tf_includes_compute_platform(self, gen: CodeDeployGenerator):
        instance = _make_codedeploy_instance(compute_platform="Server")
        result = gen.generate_resource_tf(instance)
        assert "compute_platform" in result

    def test_variables_tf_includes_compute_platform_variable(
        self, gen: CodeDeployGenerator
    ):
        instance = _make_codedeploy_instance(compute_platform="Server")
        result = gen.generate_variables_tf(instance)
        assert "compute_platform" in result
