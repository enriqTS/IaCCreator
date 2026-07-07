"""Unit tests for CodePipelineGenerator.

Requirements: 44.1–44.6
"""

import pytest

from app.generators.codepipeline_generator import CodePipelineGenerator
from app.models.input_models import ServiceType
from app.models.input_models.codepipeline_config import CodePipelineConfig
from app.models.ir_models import ResourceInstanceIR


def _make_codepipeline_instance(
    name: str = "my-pipeline",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for CodePipeline."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.CODEPIPELINE,
        config=CodePipelineConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> CodePipelineGenerator:
    return CodePipelineGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestCodePipelineGeneratorMinimal:
    """Test CodePipelineGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_codepipeline(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_codepipeline" in result

    def test_variables_tf_contains_pipeline_name(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance()
        result = gen.generate_variables_tf(instance)
        assert "pipeline_name" in result

    def test_outputs_tf_contains_pipeline_arn(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance()
        result = gen.generate_outputs_tf(instance)
        assert "pipeline_arn" in result

    def test_outputs_tf_contains_pipeline_name(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance()
        result = gen.generate_outputs_tf(instance)
        assert "pipeline_name" in result

    def test_resource_tf_no_role_arn_when_not_set(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance()
        result = gen.generate_resource_tf(instance)
        assert "role_arn" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestCodePipelineGeneratorWithOptionalConfig:
    """Test CodePipelineGenerator with optional config fields set."""

    def test_resource_tf_includes_role_arn(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance(role_arn="arn:aws:iam::role/cp")
        result = gen.generate_resource_tf(instance)
        assert "role_arn" in result

    def test_variables_tf_includes_role_arn_variable(self, gen: CodePipelineGenerator):
        instance = _make_codepipeline_instance(role_arn="arn:aws:iam::role/cp")
        result = gen.generate_variables_tf(instance)
        assert "role_arn" in result
