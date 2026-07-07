"""Unit tests for CodeCommitGenerator.

Requirements: 40.1–40.5
"""

import pytest

from app.generators.codecommit_generator import CodeCommitGenerator
from app.models.input_models import ServiceType
from app.models.input_models.codecommit_config import CodeCommitConfig
from app.models.ir_models import ResourceInstanceIR


def _make_codecommit_instance(
    name: str = "my-repo",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for CodeCommit."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.CODECOMMIT,
        config=CodeCommitConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> CodeCommitGenerator:
    return CodeCommitGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestCodeCommitGeneratorMinimal:
    """Test CodeCommitGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_codecommit_repository(
        self, gen: CodeCommitGenerator
    ):
        instance = _make_codecommit_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_codecommit_repository" in result

    def test_variables_tf_contains_repository_name(self, gen: CodeCommitGenerator):
        instance = _make_codecommit_instance()
        result = gen.generate_variables_tf(instance)
        assert "repository_name" in result

    def test_outputs_tf_contains_repository_arn(self, gen: CodeCommitGenerator):
        instance = _make_codecommit_instance()
        result = gen.generate_outputs_tf(instance)
        assert "repository_arn" in result

    def test_outputs_tf_contains_clone_url_http(self, gen: CodeCommitGenerator):
        instance = _make_codecommit_instance()
        result = gen.generate_outputs_tf(instance)
        assert "clone_url_http" in result
