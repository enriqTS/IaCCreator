"""Unit tests for CloudSearchGenerator.

Requirements: 4.1–4.5
"""

import pytest

from app.generators.cloudsearch_generator import CloudSearchGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_cloudsearch_instance(
    name: str = "my-domain",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for CloudSearch."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.CLOUDSEARCH,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> CloudSearchGenerator:
    return CloudSearchGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestCloudSearchGeneratorMinimal:
    """Test CloudSearchGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_cloudsearch_domain(
        self, gen: CloudSearchGenerator
    ):
        instance = _make_cloudsearch_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_cloudsearch_domain" in result

    def test_variables_tf_contains_domain_name(self, gen: CloudSearchGenerator):
        instance = _make_cloudsearch_instance()
        result = gen.generate_variables_tf(instance)
        assert "domain_name" in result

    def test_outputs_tf_contains_domain_arn(self, gen: CloudSearchGenerator):
        instance = _make_cloudsearch_instance()
        result = gen.generate_outputs_tf(instance)
        assert "domain_arn" in result

    def test_outputs_tf_contains_domain_id(self, gen: CloudSearchGenerator):
        instance = _make_cloudsearch_instance()
        result = gen.generate_outputs_tf(instance)
        assert "domain_id" in result
