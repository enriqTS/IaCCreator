"""Unit tests for OpenSearchGenerator.

Requirements: 16.1–16.5
"""

import pytest

from app.generators.opensearch_generator import OpenSearchGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_opensearch_instance(
    name: str = "my-domain",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for OpenSearch."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.OPENSEARCH,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> OpenSearchGenerator:
    return OpenSearchGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestOpenSearchGeneratorMinimal:
    """Test OpenSearchGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_opensearch_domain(self, gen: OpenSearchGenerator):
        instance = _make_opensearch_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_opensearch_domain" in result

    def test_variables_tf_contains_domain_name(self, gen: OpenSearchGenerator):
        instance = _make_opensearch_instance()
        result = gen.generate_variables_tf(instance)
        assert "domain_name" in result

    def test_outputs_tf_contains_domain_arn(self, gen: OpenSearchGenerator):
        instance = _make_opensearch_instance()
        result = gen.generate_outputs_tf(instance)
        assert "domain_arn" in result

    def test_outputs_tf_contains_domain_endpoint(self, gen: OpenSearchGenerator):
        instance = _make_opensearch_instance()
        result = gen.generate_outputs_tf(instance)
        assert "domain_endpoint" in result
