"""Unit tests for ECRGenerator.

Requirements: 18.1–18.7
"""

import pytest

from app.generators.ecr_generator import ECRGenerator
from app.models.input_models import ServiceType
from app.models.input_models.ecr_config import EcrConfig
from app.models.ir_models import ResourceInstanceIR


def _make_ecr_instance(
    name: str = "my-repo",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for ECR."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.ECR,
        config=EcrConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> ECRGenerator:
    return ECRGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestECRGeneratorMinimal:
    """Test ECRGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_ecr_repository(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_ecr_repository" in result

    def test_resource_tf_references_repository_name(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.repository_name" in result

    def test_variables_tf_contains_required_variables(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_variables_tf(instance)
        assert "repository_name" in result

    def test_outputs_tf_contains_repository_arn(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_outputs_tf(instance)
        assert "repository_arn" in result

    def test_outputs_tf_contains_repository_url(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_outputs_tf(instance)
        assert "repository_url" in result

    def test_resource_tf_no_image_tag_mutability_when_not_set(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_resource_tf(instance)
        assert "image_tag_mutability" not in result

    def test_resource_tf_no_scan_on_push_when_not_set(self, gen: ECRGenerator):
        instance = _make_ecr_instance()
        result = gen.generate_resource_tf(instance)
        assert "image_scanning_configuration" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestECRGeneratorWithOptionalConfig:
    """Test ECRGenerator with optional config fields set."""

    def test_resource_tf_includes_image_tag_mutability(self, gen: ECRGenerator):
        instance = _make_ecr_instance(ecr_image_tag_mutability="IMMUTABLE")
        result = gen.generate_resource_tf(instance)
        assert "image_tag_mutability" in result

    def test_resource_tf_includes_scan_on_push(self, gen: ECRGenerator):
        instance = _make_ecr_instance(ecr_scan_on_push=True)
        result = gen.generate_resource_tf(instance)
        assert "scan_on_push" in result

    def test_variables_tf_includes_image_tag_mutability_variable(
        self, gen: ECRGenerator
    ):
        instance = _make_ecr_instance(ecr_image_tag_mutability="IMMUTABLE")
        result = gen.generate_variables_tf(instance)
        assert "ecr_image_tag_mutability" in result

    def test_variables_tf_includes_scan_on_push_variable(self, gen: ECRGenerator):
        instance = _make_ecr_instance(ecr_scan_on_push=True)
        result = gen.generate_variables_tf(instance)
        assert "ecr_scan_on_push" in result
