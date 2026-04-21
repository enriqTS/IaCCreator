"""Unit tests for EC2Generator.

Requirements: 2.1–2.6
"""

import pytest

from app.generators.ec2_generator import EC2Generator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_ec2_instance(
    name: str = "my-server",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for EC2."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.EC2,
        config=ResourceConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> EC2Generator:
    return EC2Generator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------

class TestEC2GeneratorMinimal:
    """Test EC2Generator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_instance(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_instance" in result

    def test_resource_tf_references_ami_variable(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.ami" in result

    def test_resource_tf_references_instance_type_variable(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.instance_type" in result

    def test_variables_tf_contains_required_variables(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_variables_tf(instance)
        assert "instance_name" in result
        assert "ami" in result
        assert "instance_type" in result

    def test_outputs_tf_contains_instance_id(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_outputs_tf(instance)
        assert "instance_id" in result

    def test_outputs_tf_contains_public_ip(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_outputs_tf(instance)
        assert "public_ip" in result

    def test_resource_tf_no_key_name_when_not_set(self, gen: EC2Generator):
        instance = _make_ec2_instance()
        result = gen.generate_resource_tf(instance)
        assert "key_name" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------

class TestEC2GeneratorWithOptionalConfig:
    """Test EC2Generator with optional config fields set."""

    def test_resource_tf_includes_key_name(self, gen: EC2Generator):
        instance = _make_ec2_instance(key_name="my-key")
        result = gen.generate_resource_tf(instance)
        assert "key_name" in result

    def test_variables_tf_includes_key_name_variable(self, gen: EC2Generator):
        instance = _make_ec2_instance(key_name="my-key")
        result = gen.generate_variables_tf(instance)
        assert "key_name" in result
