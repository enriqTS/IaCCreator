"""Unit tests for EC2ImageBuilderGenerator.

Requirements: 14.1–14.5
"""

import pytest

from app.generators.ec2_image_builder_generator import EC2ImageBuilderGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_imagebuilder_instance(
    name: str = "my-pipeline",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for EC2 Image Builder."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.EC2_IMAGE_BUILDER,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> EC2ImageBuilderGenerator:
    return EC2ImageBuilderGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestEC2ImageBuilderGeneratorMinimal:
    """Test EC2ImageBuilderGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_imagebuilder_pipeline(self, gen: EC2ImageBuilderGenerator):
        instance = _make_imagebuilder_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_imagebuilder_image_pipeline" in result

    def test_resource_tf_references_pipeline_name(self, gen: EC2ImageBuilderGenerator):
        instance = _make_imagebuilder_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.pipeline_name" in result

    def test_resource_tf_references_image_recipe_arn(self, gen: EC2ImageBuilderGenerator):
        instance = _make_imagebuilder_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.image_recipe_arn" in result

    def test_resource_tf_references_infrastructure_configuration_arn(self, gen: EC2ImageBuilderGenerator):
        instance = _make_imagebuilder_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.infrastructure_configuration_arn" in result

    def test_variables_tf_contains_required_variables(self, gen: EC2ImageBuilderGenerator):
        instance = _make_imagebuilder_instance()
        result = gen.generate_variables_tf(instance)
        assert "pipeline_name" in result
        assert "image_recipe_arn" in result
        assert "infrastructure_configuration_arn" in result

    def test_outputs_tf_contains_pipeline_arn(self, gen: EC2ImageBuilderGenerator):
        instance = _make_imagebuilder_instance()
        result = gen.generate_outputs_tf(instance)
        assert "pipeline_arn" in result
