"""Unit tests for the IRBuilder service."""

import pytest

from app.exceptions import IncompatibleConnectionError, ResourceNotFoundError
from app.models.input_models import (
    ArchitectureDescription,
    Connection,
    EnvironmentConfig,
    ResourceConfig,
    ResourceInstance,
    ServiceType,
)
from app.services.ir_builder import IRBuilder


def _make_input(**overrides) -> ArchitectureDescription:
    """Helper to build a minimal valid ArchitectureDescription."""
    defaults = {
        "project_name": "test-project",
        "environments": [
            EnvironmentConfig(name="dev", variables={"region": "us-east-1"})
        ],
        "resources": [
            ResourceInstance(
                name="my-func",
                service_type=ServiceType.LAMBDA,
                config=ResourceConfig(handler="index.handler", runtime="python3.12"),
            ),
        ],
        "connections": [],
    }
    defaults.update(overrides)
    return ArchitectureDescription(**defaults)


class TestIRBuilderBasic:
    """Test basic IR building from a known small input."""

    def test_build_returns_project_ir_with_correct_name(self):
        desc = _make_input()
        ir = IRBuilder().build(desc)
        assert ir.project_name == "test-project"

    def test_build_groups_resources_by_service_type(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="func-a",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="a.handler", runtime="python3.12"),
                ),
                ResourceInstance(
                    name="func-b",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="b.handler", runtime="python3.12"),
                ),
                ResourceInstance(name="my-bucket", service_type=ServiceType.S3),
            ]
        )
        ir = IRBuilder().build(desc)
        service_types = {m.service_type for m in ir.modules}
        assert service_types == {ServiceType.LAMBDA, ServiceType.S3}

        lambda_module = next(
            m for m in ir.modules if m.service_type == ServiceType.LAMBDA
        )
        assert len(lambda_module.instances) == 2

        s3_module = next(m for m in ir.modules if m.service_type == ServiceType.S3)
        assert len(s3_module.instances) == 1

    def test_build_creates_environments_with_module_refs(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="func-a",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="a.handler", runtime="python3.12"),
                ),
                ResourceInstance(
                    name="my-table",
                    service_type=ServiceType.DYNAMODB,
                    config=ResourceConfig(hash_key="id"),
                ),
            ],
            environments=[
                EnvironmentConfig(name="dev", variables={"region": "us-east-1"}),
                EnvironmentConfig(name="prod", variables={"region": "us-west-2"}),
            ],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.environments) == 2
        for env in ir.environments:
            assert ServiceType.LAMBDA in env.module_refs
            assert ServiceType.DYNAMODB in env.module_refs

    def test_build_preserves_environment_variables(self):
        desc = _make_input(
            environments=[
                EnvironmentConfig(
                    name="dev", variables={"region": "us-east-1", "stage": "dev"}
                )
            ]
        )
        ir = IRBuilder().build(desc)
        assert ir.environments[0].variables == {"region": "us-east-1", "stage": "dev"}


class TestConnectionValidation:
    """Test connection validation in IRBuilder."""

    def test_rejects_nonexistent_source_resource(self):
        desc = _make_input(
            connections=[
                Connection(source="ghost", target="my-func", connection_type="triggers")
            ]
        )
        with pytest.raises(ResourceNotFoundError) as exc_info:
            IRBuilder().build(desc)
        assert "non-existent source resource" in str(exc_info.value)

    def test_rejects_nonexistent_target_resource(self):
        desc = _make_input(
            connections=[
                Connection(source="my-func", target="ghost", connection_type="triggers")
            ]
        )
        with pytest.raises(ResourceNotFoundError) as exc_info:
            IRBuilder().build(desc)
        assert "non-existent target resource" in str(exc_info.value)

    def test_rejects_incompatible_connection_s3_to_s3(self):
        desc = _make_input(
            resources=[
                ResourceInstance(name="bucket-a", service_type=ServiceType.S3),
                ResourceInstance(name="bucket-b", service_type=ServiceType.S3),
            ],
            connections=[
                Connection(
                    source="bucket-a", target="bucket-b", connection_type="reads_from"
                )
            ],
        )
        with pytest.raises(IncompatibleConnectionError) as exc_info:
            IRBuilder().build(desc)
        assert "Incompatible connection" in str(exc_info.value)

    def test_rejects_dynamodb_to_lambda(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-table",
                    service_type=ServiceType.DYNAMODB,
                    config=ResourceConfig(hash_key="id"),
                ),
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
            ],
            connections=[
                Connection(
                    source="my-table", target="my-func", connection_type="triggers"
                )
            ],
        )
        with pytest.raises(IncompatibleConnectionError):
            IRBuilder().build(desc)

    def test_accepts_valid_api_gateway_to_lambda(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-api",
                    service_type=ServiceType.API_GATEWAY,
                    config=ResourceConfig(protocol_type="HTTP"),
                ),
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
            ],
            connections=[
                Connection(
                    source="my-api", target="my-func", connection_type="triggers"
                )
            ],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.connections) == 1
        assert ir.connections[0].source_service == ServiceType.API_GATEWAY
        assert ir.connections[0].target_service == ServiceType.LAMBDA


class TestIAMStatementDerivation:
    """Test that IRBuilder produces empty IAM statements (IAM derivation moved to ConnectionProcessor)."""

    def test_lambda_to_dynamodb_iam_statements(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
                ResourceInstance(
                    name="my-table",
                    service_type=ServiceType.DYNAMODB,
                    config=ResourceConfig(hash_key="id"),
                ),
            ],
            connections=[
                Connection(
                    source="my-func", target="my-table", connection_type="reads_from"
                )
            ],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(
            m for m in ir.modules if m.service_type == ServiceType.LAMBDA
        )
        func_ir = lambda_module.instances[0]
        assert func_ir.iam_statements == []

    def test_lambda_to_s3_iam_statements(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
                ResourceInstance(name="my-bucket", service_type=ServiceType.S3),
            ],
            connections=[
                Connection(
                    source="my-func", target="my-bucket", connection_type="writes_to"
                )
            ],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(
            m for m in ir.modules if m.service_type == ServiceType.LAMBDA
        )
        func_ir = lambda_module.instances[0]
        assert func_ir.iam_statements == []

    def test_lambda_to_cloudwatch_iam_statements(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
                ResourceInstance(name="my-logs", service_type=ServiceType.CLOUDWATCH),
            ],
            connections=[
                Connection(
                    source="my-func", target="my-logs", connection_type="logs_to"
                )
            ],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(
            m for m in ir.modules if m.service_type == ServiceType.LAMBDA
        )
        func_ir = lambda_module.instances[0]
        assert func_ir.iam_statements == []

    def test_multiple_connections_produce_empty_iam_statements(self):
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
                ResourceInstance(
                    name="my-table",
                    service_type=ServiceType.DYNAMODB,
                    config=ResourceConfig(hash_key="id"),
                ),
                ResourceInstance(name="my-bucket", service_type=ServiceType.S3),
            ],
            connections=[
                Connection(
                    source="my-func", target="my-table", connection_type="reads_from"
                ),
                Connection(
                    source="my-func", target="my-bucket", connection_type="writes_to"
                ),
            ],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(
            m for m in ir.modules if m.service_type == ServiceType.LAMBDA
        )
        func_ir = lambda_module.instances[0]
        assert func_ir.iam_statements == []

    def test_api_gateway_to_lambda_no_iam_on_gateway(self):
        """API Gateway → Lambda should not add IAM statements to the gateway resource."""
        desc = _make_input(
            resources=[
                ResourceInstance(
                    name="my-api",
                    service_type=ServiceType.API_GATEWAY,
                    config=ResourceConfig(protocol_type="HTTP"),
                ),
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                ),
            ],
            connections=[
                Connection(
                    source="my-api", target="my-func", connection_type="triggers"
                )
            ],
        )
        ir = IRBuilder().build(desc)
        api_module = next(
            m for m in ir.modules if m.service_type == ServiceType.API_GATEWAY
        )
        api_ir = api_module.instances[0]
        assert len(api_ir.iam_statements) == 0
