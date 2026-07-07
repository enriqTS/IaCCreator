"""Unit tests for GlueGenerator.

Requirements: 8.1–8.5
"""

import pytest

from app.generators.glue_generator import GlueGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_glue_instance(
    name: str = "my-database",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Glue."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.GLUE,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> GlueGenerator:
    return GlueGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestGlueGeneratorMinimal:
    """Test GlueGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_glue_catalog_database(self, gen: GlueGenerator):
        instance = _make_glue_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_glue_catalog_database" in result

    def test_variables_tf_contains_database_name(self, gen: GlueGenerator):
        instance = _make_glue_instance()
        result = gen.generate_variables_tf(instance)
        assert "database_name" in result

    def test_outputs_tf_contains_database_name(self, gen: GlueGenerator):
        instance = _make_glue_instance()
        result = gen.generate_outputs_tf(instance)
        assert "database_name" in result

    def test_outputs_tf_contains_catalog_id(self, gen: GlueGenerator):
        instance = _make_glue_instance()
        result = gen.generate_outputs_tf(instance)
        assert "catalog_id" in result
