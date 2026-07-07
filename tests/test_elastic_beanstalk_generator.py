"""Unit tests for ElasticBeanstalkGenerator.

Requirements: 8.1–8.7
"""

import pytest

from app.generators.elastic_beanstalk_generator import ElasticBeanstalkGenerator
from app.models.input_models import ServiceType
from app.models.input_models.elastic_beanstalk_config import ElasticBeanstalkConfig
from app.models.ir_models import ResourceInstanceIR


def _make_eb_instance(
    name: str = "my-app",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Elastic Beanstalk."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.ELASTIC_BEANSTALK,
        config=ElasticBeanstalkConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> ElasticBeanstalkGenerator:
    return ElasticBeanstalkGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestElasticBeanstalkGeneratorMinimal:
    """Test ElasticBeanstalkGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_application(self, gen: ElasticBeanstalkGenerator):
        instance = _make_eb_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_elastic_beanstalk_application" in result

    def test_resource_tf_contains_environment(self, gen: ElasticBeanstalkGenerator):
        instance = _make_eb_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_elastic_beanstalk_environment" in result

    def test_variables_tf_contains_required_variables(
        self, gen: ElasticBeanstalkGenerator
    ):
        instance = _make_eb_instance()
        result = gen.generate_variables_tf(instance)
        assert "application_name" in result
        assert "environment_name" in result

    def test_outputs_tf_contains_application_name(self, gen: ElasticBeanstalkGenerator):
        instance = _make_eb_instance()
        result = gen.generate_outputs_tf(instance)
        assert "application_name" in result

    def test_outputs_tf_contains_environment_endpoint(
        self, gen: ElasticBeanstalkGenerator
    ):
        instance = _make_eb_instance()
        result = gen.generate_outputs_tf(instance)
        assert "environment_endpoint" in result

    def test_resource_tf_no_solution_stack_when_not_set(
        self, gen: ElasticBeanstalkGenerator
    ):
        instance = _make_eb_instance()
        result = gen.generate_resource_tf(instance)
        assert "solution_stack_name" not in result

    def test_resource_tf_no_tier_when_not_set(self, gen: ElasticBeanstalkGenerator):
        instance = _make_eb_instance()
        result = gen.generate_resource_tf(instance)
        assert "tier" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestElasticBeanstalkGeneratorWithOptionalConfig:
    """Test ElasticBeanstalkGenerator with optional config fields set."""

    def test_resource_tf_includes_solution_stack_name(
        self, gen: ElasticBeanstalkGenerator
    ):
        instance = _make_eb_instance(
            eb_solution_stack_name="64bit Amazon Linux 2 v5.8.0 running Node.js 18"
        )
        result = gen.generate_resource_tf(instance)
        assert "solution_stack_name" in result

    def test_resource_tf_includes_tier(self, gen: ElasticBeanstalkGenerator):
        instance = _make_eb_instance(eb_tier="WebServer")
        result = gen.generate_resource_tf(instance)
        assert "tier" in result

    def test_variables_tf_includes_solution_stack_variable(
        self, gen: ElasticBeanstalkGenerator
    ):
        instance = _make_eb_instance(
            eb_solution_stack_name="64bit Amazon Linux 2 v5.8.0 running Node.js 18"
        )
        result = gen.generate_variables_tf(instance)
        assert "eb_solution_stack_name" in result

    def test_variables_tf_includes_tier_variable(self, gen: ElasticBeanstalkGenerator):
        instance = _make_eb_instance(eb_tier="WebServer")
        result = gen.generate_variables_tf(instance)
        assert "eb_tier" in result
