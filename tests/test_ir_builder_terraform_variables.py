"""Unit and property tests for IRBuilder terraform_variables propagation.

Validates Requirements 7.2 and 7.3:
- terraform_variables pass through from ResourceInstance to ResourceInstanceIR
- Missing terraform_variables get schema defaults
- Property 2: All ResourceInstanceIR objects have terraform_variables populated after build
"""

from hypothesis import given, settings

from app.models.input_models import (
    ArchitectureDescription,
    EnvironmentConfig,
    GlobalTerraformConfig,
    ResourceInstance,
    ServiceType,
)
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.services.ir_builder import IRBuilder
from tests.conftest import architecture_description_strategy


def _make_input(**overrides) -> ArchitectureDescription:
    defaults = {
        "project_name": "test-project",
        "environments": [
            EnvironmentConfig(name="dev", variables={"region": "us-east-1"})
        ],
        "resources": [
            ResourceInstance(
                name="my-func",
                service_type=ServiceType.LAMBDA,
                config=LambdaConfig(handler="index.handler", runtime="python3.12"),
            ),
        ],
        "connections": [],
    }
    defaults.update(overrides)
    return ArchitectureDescription(**defaults)


def _get_instance_ir(ir, name):
    for module in ir.modules:
        for inst in module.instances:
            if inst.name == name:
                return inst
    return None


class TestTerraformVariablesPropagation:
    """Test that terraform_variables pass through from input to IR."""

    def test_explicit_variables_propagate_to_ir(self):
        """Variables provided on ResourceInstance appear on ResourceInstanceIR."""
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=LambdaConfig(
                        handler="index.handler", runtime="python3.12"
                    ),
                    terraform_variables={
                        "function_name": "hello",
                        "memory_size": 256,
                        "timeout": 10,
                    },
                ),
            ]
        )
        ir = IRBuilder().build(desc)
        inst = _get_instance_ir(ir, "my-func")
        assert inst is not None
        assert inst.terraform_variables["function_name"] == "hello"
        assert inst.terraform_variables["memory_size"] == 256
        assert inst.terraform_variables["timeout"] == 10

    def test_variables_propagate_for_multiple_service_types(self):
        """Variables propagate correctly across different service types."""
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=LambdaConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"function_name": "fn1", "handler": "h"},
                ),
                ResourceInstance(
                    name="my-bucket",
                    service_type=ServiceType.S3,
                    terraform_variables={
                        "bucket_name": "test-bucket",
                        "versioning_enabled": True,
                    },
                ),
                ResourceInstance(
                    name="my-table",
                    service_type=ServiceType.DYNAMODB,
                    config=DynamoDBConfig(hash_key="id"),
                    terraform_variables={
                        "table_name": "users",
                        "billing_mode": "PAY_PER_REQUEST",
                    },
                ),
            ]
        )
        ir = IRBuilder().build(desc)

        func_ir = _get_instance_ir(ir, "my-func")
        assert func_ir.terraform_variables["function_name"] == "fn1"

        bucket_ir = _get_instance_ir(ir, "my-bucket")
        assert bucket_ir.terraform_variables["bucket_name"] == "test-bucket"
        assert bucket_ir.terraform_variables["versioning_enabled"] is True

        table_ir = _get_instance_ir(ir, "my-table")
        assert table_ir.terraform_variables["table_name"] == "users"

    def test_empty_variables_propagate_as_empty_dict(self):
        """When no terraform_variables are provided, an empty dict propagates."""
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=LambdaConfig(handler="h", runtime="python3.12"),
                ),
            ]
        )
        ir = IRBuilder().build(desc)
        inst = _get_instance_ir(ir, "my-func")
        assert inst.terraform_variables == {}

    def test_bool_variables_preserve_type(self):
        """Bool values remain booleans through propagation."""
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-bucket",
                    service_type=ServiceType.S3,
                    terraform_variables={"versioning_enabled": False},
                ),
            ]
        )
        ir = IRBuilder().build(desc)
        inst = _get_instance_ir(ir, "my-bucket")
        assert inst.terraform_variables["versioning_enabled"] is False
        assert isinstance(inst.terraform_variables["versioning_enabled"], bool)

    def test_number_variables_preserve_type(self):
        """Numeric values remain the correct numeric type through propagation."""
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=LambdaConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"memory_size": 512, "timeout": 30},
                ),
            ]
        )
        ir = IRBuilder().build(desc)
        inst = _get_instance_ir(ir, "my-func")
        assert inst.terraform_variables["memory_size"] == 512
        assert isinstance(inst.terraform_variables["memory_size"], int)


class TestGlobalConfigPropagation:
    """Test that global_terraform_config propagates from input to IR."""

    def test_global_config_propagates_to_project_ir(self):
        desc = _make_input()
        desc.global_terraform_config = GlobalTerraformConfig(
            backend_type="s3",
            backend_config={
                "bucket": "my-state",
                "key": "terraform.tfstate",
                "region": "us-east-1",
            },
            provider_region="eu-west-1",
            provider_profile="prod",
            terraform_version=">= 1.5.0",
            aws_provider_version="~> 5.0",
        )
        ir = IRBuilder().build(desc)
        assert ir.global_config.backend_type == "s3"
        assert ir.global_config.backend_config["bucket"] == "my-state"
        assert ir.global_config.provider_region == "eu-west-1"
        assert ir.global_config.provider_profile == "prod"
        assert ir.global_config.terraform_version == ">= 1.5.0"
        assert ir.global_config.aws_provider_version == "~> 5.0"

    def test_default_global_config_when_not_provided(self):
        desc = _make_input()
        ir = IRBuilder().build(desc)
        assert ir.global_config.backend_type == "local"
        assert ir.global_config.backend_config == {}
        assert ir.global_config.provider_region == "us-east-1"
        assert ir.global_config.provider_profile is None
        assert ir.global_config.terraform_version is None
        assert ir.global_config.aws_provider_version is None


# ---------------------------------------------------------------------------
# Property 2: All ResourceInstanceIR objects have terraform_variables populated
# ---------------------------------------------------------------------------


@given(arch=architecture_description_strategy())
@settings(max_examples=50)
def test_property_2_all_ir_instances_have_terraform_variables(arch):
    """Property: After IRBuilder.build(), every ResourceInstanceIR has a
    terraform_variables dict (never None). This validates that the field
    is always initialized regardless of input."""
    ir = IRBuilder().build(arch)
    for module in ir.modules:
        for instance in module.instances:
            assert instance.terraform_variables is not None
            assert isinstance(instance.terraform_variables, dict)
