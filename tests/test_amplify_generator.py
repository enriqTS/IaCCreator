"""Unit tests for AmplifyGenerator.

Requirements: 48.1–48.5
"""

import pytest

from app.generators.amplify_generator import AmplifyGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_amplify_instance(
    name: str = "my-app",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Amplify."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.AMPLIFY,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> AmplifyGenerator:
    return AmplifyGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestAmplifyGeneratorMinimal:
    """Test AmplifyGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_amplify_app(self, gen: AmplifyGenerator):
        instance = _make_amplify_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_amplify_app" in result

    def test_variables_tf_contains_app_name(self, gen: AmplifyGenerator):
        instance = _make_amplify_instance()
        result = gen.generate_variables_tf(instance)
        assert "app_name" in result

    def test_outputs_tf_contains_app_id(self, gen: AmplifyGenerator):
        instance = _make_amplify_instance()
        result = gen.generate_outputs_tf(instance)
        assert "app_id" in result

    def test_outputs_tf_contains_app_arn(self, gen: AmplifyGenerator):
        instance = _make_amplify_instance()
        result = gen.generate_outputs_tf(instance)
        assert "app_arn" in result
