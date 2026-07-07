"""Unit tests for GameLiftGenerator.

Requirements: 50.1–50.6
"""

import pytest

from app.generators.gamelift_generator import GameLiftGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_gamelift_instance(
    name: str = "my-fleet",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for GameLift."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.GAMELIFT,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> GameLiftGenerator:
    return GameLiftGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestGameLiftGeneratorMinimal:
    """Test GameLiftGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_gamelift_fleet(self, gen: GameLiftGenerator):
        instance = _make_gamelift_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_gamelift_fleet" in result

    def test_variables_tf_contains_fleet_name(self, gen: GameLiftGenerator):
        instance = _make_gamelift_instance()
        result = gen.generate_variables_tf(instance)
        assert "fleet_name" in result

    def test_outputs_tf_contains_fleet_arn(self, gen: GameLiftGenerator):
        instance = _make_gamelift_instance()
        result = gen.generate_outputs_tf(instance)
        assert "fleet_arn" in result

    def test_outputs_tf_contains_fleet_id(self, gen: GameLiftGenerator):
        instance = _make_gamelift_instance()
        result = gen.generate_outputs_tf(instance)
        assert "fleet_id" in result

    def test_resource_tf_no_ec2_instance_type_when_not_set(
        self, gen: GameLiftGenerator
    ):
        instance = _make_gamelift_instance()
        result = gen.generate_resource_tf(instance)
        assert "ec2_instance_type" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestGameLiftGeneratorWithOptionalConfig:
    """Test GameLiftGenerator with optional config fields set."""

    def test_resource_tf_includes_ec2_instance_type(self, gen: GameLiftGenerator):
        instance = _make_gamelift_instance(gamelift_ec2_instance_type="c5.large")
        result = gen.generate_resource_tf(instance)
        assert "ec2_instance_type" in result

    def test_variables_tf_includes_ec2_instance_type_variable(
        self, gen: GameLiftGenerator
    ):
        instance = _make_gamelift_instance(gamelift_ec2_instance_type="c5.large")
        result = gen.generate_variables_tf(instance)
        assert "ec2_instance_type" in result
