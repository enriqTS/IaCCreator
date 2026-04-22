"""Unit tests for DocumentDBGenerator.

Requirements: 28.1–28.6
"""

import pytest

from app.generators.documentdb_generator import DocumentDBGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_documentdb_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for DocumentDB."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.DOCUMENTDB,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> DocumentDBGenerator:
    return DocumentDBGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestDocumentDBGeneratorMinimal:
    """Test DocumentDBGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_docdb_cluster(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_docdb_cluster" in result

    def test_variables_tf_contains_cluster_identifier(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_identifier" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_cluster_endpoint(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_endpoint" in result

    def test_resource_tf_no_master_username_when_not_set(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance()
        result = gen.generate_resource_tf(instance)
        assert "master_username" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------

class TestDocumentDBGeneratorWithOptionalConfig:
    """Test DocumentDBGenerator with optional config fields set."""

    def test_resource_tf_includes_master_username(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance(documentdb_master_username="admin")
        result = gen.generate_resource_tf(instance)
        assert "master_username" in result

    def test_variables_tf_includes_master_username_variable(self, gen: DocumentDBGenerator):
        instance = _make_documentdb_instance(documentdb_master_username="admin")
        result = gen.generate_variables_tf(instance)
        assert "master_username" in result
