"""Unit tests for ConnectGenerator.

Requirements: 20.1–20.8
"""

import pytest

from app.generators.connect_generator import ConnectGenerator
from app.models.input_models import ServiceType
from app.models.input_models.connect_config import ConnectConfig
from app.models.ir_models import ResourceInstanceIR


def _make_connect_instance(
    name: str = "my-instance",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Connect."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.CONNECT,
        config=ConnectConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> ConnectGenerator:
    return ConnectGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestConnectGeneratorMinimal:
    """Test ConnectGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_aws_connect_instance(self, gen: ConnectGenerator):
        instance = _make_connect_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_connect_instance" in result

    def test_outputs_tf_contains_instance_id(self, gen: ConnectGenerator):
        instance = _make_connect_instance()
        result = gen.generate_outputs_tf(instance)
        assert "instance_id" in result

    def test_outputs_tf_contains_instance_arn(self, gen: ConnectGenerator):
        instance = _make_connect_instance()
        result = gen.generate_outputs_tf(instance)
        assert "instance_arn" in result

    def test_resource_tf_no_identity_management_type_when_not_set(
        self, gen: ConnectGenerator
    ):
        instance = _make_connect_instance()
        result = gen.generate_resource_tf(instance)
        assert "identity_management_type" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestConnectGeneratorWithOptionalConfig:
    """Test ConnectGenerator with optional config fields set."""

    def test_resource_tf_includes_identity_management_type(self, gen: ConnectGenerator):
        instance = _make_connect_instance(identity_management_type="SAML")
        result = gen.generate_resource_tf(instance)
        assert "identity_management_type" in result

    def test_variables_tf_includes_identity_management_type_variable(
        self, gen: ConnectGenerator
    ):
        instance = _make_connect_instance(identity_management_type="SAML")
        result = gen.generate_variables_tf(instance)
        assert "identity_management_type" in result

    def test_resource_tf_includes_inbound_calls_enabled(self, gen: ConnectGenerator):
        instance = _make_connect_instance(inbound_calls_enabled=True)
        result = gen.generate_resource_tf(instance)
        assert "inbound_calls_enabled" in result

    def test_resource_tf_includes_outbound_calls_enabled(self, gen: ConnectGenerator):
        instance = _make_connect_instance(outbound_calls_enabled=True)
        result = gen.generate_resource_tf(instance)
        assert "outbound_calls_enabled" in result
