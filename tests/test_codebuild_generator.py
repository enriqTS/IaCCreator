"""Unit tests for CodeBuildGenerator.

Requirements: 38.1–38.8
"""

import pytest

from app.generators.codebuild_generator import CodeBuildGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_codebuild_instance(
    name: str = "my-project",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for CodeBuild."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.CODEBUILD,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> CodeBuildGenerator:
    return CodeBuildGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestCodeBuildGeneratorMinimal:
    """Test CodeBuildGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_codebuild_project(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_codebuild_project" in result

    def test_variables_tf_contains_project_name(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance()
        result = gen.generate_variables_tf(instance)
        assert "project_name" in result

    def test_outputs_tf_contains_project_arn(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance()
        result = gen.generate_outputs_tf(instance)
        assert "project_arn" in result

    def test_outputs_tf_contains_project_name(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance()
        result = gen.generate_outputs_tf(instance)
        assert "project_name" in result

    def test_resource_tf_no_source_block_when_not_set(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance()
        result = gen.generate_resource_tf(instance)
        assert "source_type" not in result

    def test_resource_tf_no_service_role_when_not_set(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance()
        result = gen.generate_resource_tf(instance)
        assert "service_role" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------

class TestCodeBuildGeneratorWithOptionalConfig:
    """Test CodeBuildGenerator with optional config fields set."""

    def test_resource_tf_includes_source_type(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance(codebuild_source_type="GITHUB")
        result = gen.generate_resource_tf(instance)
        assert "source" in result
        assert "type" in result

    def test_variables_tf_includes_source_type_variable(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance(codebuild_source_type="GITHUB")
        result = gen.generate_variables_tf(instance)
        assert "source_type" in result

    def test_resource_tf_includes_service_role(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance(codebuild_service_role="arn:aws:iam::role/cb")
        result = gen.generate_resource_tf(instance)
        assert "service_role" in result

    def test_variables_tf_includes_service_role_variable(self, gen: CodeBuildGenerator):
        instance = _make_codebuild_instance(codebuild_service_role="arn:aws:iam::role/cb")
        result = gen.generate_variables_tf(instance)
        assert "service_role" in result
