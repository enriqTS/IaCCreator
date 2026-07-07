"""Unit tests for RDSGenerator.

Requirements: 34.1–34.9
"""

import pytest

from app.generators.rds_generator import RDSGenerator
from app.models.input_models._general import ServiceType
from app.models.input_models.rds_config import RdsConfig
from app.models.ir_models import ResourceInstanceIR


def _make_rds_instance(
    name: str = "my-db",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for RDS."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.RDS,
        config=RdsConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> RDSGenerator:
    return RDSGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestRDSGeneratorMinimal:
    """Test RDSGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_db_instance(self, gen: RDSGenerator):
        instance = _make_rds_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_db_instance" in result

    def test_variables_tf_contains_db_identifier(self, gen: RDSGenerator):
        instance = _make_rds_instance()
        result = gen.generate_variables_tf(instance)
        assert "db_identifier" in result

    def test_outputs_tf_contains_db_instance_arn(self, gen: RDSGenerator):
        instance = _make_rds_instance()
        result = gen.generate_outputs_tf(instance)
        assert "db_instance_arn" in result

    def test_outputs_tf_contains_db_instance_endpoint(self, gen: RDSGenerator):
        instance = _make_rds_instance()
        result = gen.generate_outputs_tf(instance)
        assert "db_instance_endpoint" in result

    def test_resource_tf_no_engine_when_not_set(self, gen: RDSGenerator):
        instance = _make_rds_instance(instance_class=None, allocated_storage=None)
        result = gen.generate_resource_tf(instance)
        assert "engine" not in result

    def test_resource_tf_no_instance_class_when_not_set(self, gen: RDSGenerator):
        instance = _make_rds_instance(instance_class=None, allocated_storage=None)
        result = gen.generate_resource_tf(instance)
        assert "instance_class" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestRDSGeneratorWithOptionalConfig:
    """Test RDSGenerator with optional config fields set."""

    def test_resource_tf_includes_engine(self, gen: RDSGenerator):
        instance = _make_rds_instance(engine="mysql")
        result = gen.generate_resource_tf(instance)
        assert "engine" in result

    def test_variables_tf_includes_engine_variable(self, gen: RDSGenerator):
        instance = _make_rds_instance(engine="mysql")
        result = gen.generate_variables_tf(instance)
        assert "engine" in result

    def test_resource_tf_includes_instance_class(self, gen: RDSGenerator):
        instance = _make_rds_instance(instance_class="db.t3.micro")
        result = gen.generate_resource_tf(instance)
        assert "instance_class" in result

    def test_resource_tf_includes_allocated_storage(self, gen: RDSGenerator):
        instance = _make_rds_instance(allocated_storage=20)
        result = gen.generate_resource_tf(instance)
        assert "allocated_storage" in result

    def test_resource_tf_includes_username(self, gen: RDSGenerator):
        instance = _make_rds_instance(username="admin")
        result = gen.generate_resource_tf(instance)
        assert "username" in result
