"""Unit tests for SESGenerator.

Requirements: 22.1–22.5
"""

import pytest

from app.generators.ses_generator import SESGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_ses_instance(
    name: str = "my-domain",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for SES."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.SES,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> SESGenerator:
    return SESGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestSESGeneratorMinimal:
    """Test SESGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_ses_domain_identity(self, gen: SESGenerator):
        instance = _make_ses_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_ses_domain_identity" in result

    def test_variables_tf_contains_domain(self, gen: SESGenerator):
        instance = _make_ses_instance()
        result = gen.generate_variables_tf(instance)
        assert "domain" in result

    def test_outputs_tf_contains_domain_arn(self, gen: SESGenerator):
        instance = _make_ses_instance()
        result = gen.generate_outputs_tf(instance)
        assert "domain_arn" in result

    def test_outputs_tf_contains_verification_token(self, gen: SESGenerator):
        instance = _make_ses_instance()
        result = gen.generate_outputs_tf(instance)
        assert "verification_token" in result
