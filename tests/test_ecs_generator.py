"""Unit tests for ECSGenerator.

Requirements: 4.1–4.8
"""

import pytest

from app.generators.ecs_generator import ECSGenerator
from app.models.input_models import ServiceType
from app.models.input_models.ecs_config import EcsConfig
from app.models.ir_models import ResourceInstanceIR


def _make_ecs_instance(
    name: str = "my-ecs",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for ECS."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.ECS,
        config=EcsConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> ECSGenerator:
    return ECSGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestECSGeneratorMinimal:
    """Test ECSGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_ecs_cluster(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_ecs_cluster" in result

    def test_resource_tf_contains_task_definition(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_ecs_task_definition" in result

    def test_resource_tf_contains_ecs_service(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_ecs_service" in result

    def test_variables_tf_contains_required_variables(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_name" in result
        assert "task_family" in result
        assert "ecs_cpu" in result
        assert "ecs_memory" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_service_name(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_outputs_tf(instance)
        assert "service_name" in result

    def test_resource_tf_no_launch_type_when_not_set(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_resource_tf(instance)
        assert "launch_type" not in result

    def test_resource_tf_no_desired_count_when_not_set(self, gen: ECSGenerator):
        instance = _make_ecs_instance()
        result = gen.generate_resource_tf(instance)
        assert "desired_count" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestECSGeneratorWithOptionalConfig:
    """Test ECSGenerator with optional config fields set."""

    def test_resource_tf_includes_launch_type(self, gen: ECSGenerator):
        instance = _make_ecs_instance(ecs_launch_type="FARGATE")
        result = gen.generate_resource_tf(instance)
        assert "launch_type" in result

    def test_resource_tf_includes_desired_count(self, gen: ECSGenerator):
        instance = _make_ecs_instance(ecs_desired_count=3)
        result = gen.generate_resource_tf(instance)
        assert "desired_count" in result

    def test_variables_tf_includes_launch_type_variable(self, gen: ECSGenerator):
        instance = _make_ecs_instance(ecs_launch_type="FARGATE")
        result = gen.generate_variables_tf(instance)
        assert "ecs_launch_type" in result

    def test_variables_tf_includes_desired_count_variable(self, gen: ECSGenerator):
        instance = _make_ecs_instance(ecs_desired_count=3)
        result = gen.generate_variables_tf(instance)
        assert "ecs_desired_count" in result
