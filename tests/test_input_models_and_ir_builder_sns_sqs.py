"""Unit tests for SNS/SQS input model fields and IR Builder changes.

Covers task 1.5 of the connection-aware-terraform-generation spec:
- ServiceType enum values for SNS and SQS
- Connection model connection_config defaults and usage
- ConnectionIR carries connection_config through
- IR Builder compatible pairs for new service types
- IR Builder rejection of unsupported pairs
- _build_iam_resources ARN references for SNS and SQS
"""

import pytest
from fastapi import HTTPException

from app.models.input_models import (
    ArchitectureDescription,
    Connection,
    EnvironmentConfig,
    ResourceConfig,
    ResourceInstance,
    ServiceType,
)
from app.models.ir_models import ConnectionIR
from app.services.ir_builder import IRBuilder, _build_iam_resources


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(**overrides) -> ArchitectureDescription:
    """Build a minimal valid ArchitectureDescription with sensible defaults."""
    defaults = {
        "project_name": "test-project",
        "environments": [EnvironmentConfig(name="dev", variables={"region": "us-east-1"})],
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


def _lambda_resource(name: str = "my-func") -> ResourceInstance:
    return ResourceInstance(
        name=name,
        service_type=ServiceType.LAMBDA,
        config=ResourceConfig(handler="index.handler", runtime="python3.12"),
    )


def _sns_resource(name: str = "my-topic") -> ResourceInstance:
    return ResourceInstance(name=name, service_type=ServiceType.SNS)


def _sqs_resource(name: str = "my-queue") -> ResourceInstance:
    return ResourceInstance(name=name, service_type=ServiceType.SQS)


# ===========================================================================
# 1. ServiceType enum values
# ===========================================================================

class TestServiceTypeEnumValues:
    """Test that SNS and SQS exist as valid ServiceType values."""

    def test_sns_enum_value(self):
        assert ServiceType.SNS == "sns"
        assert ServiceType.SNS.value == "sns"

    def test_sqs_enum_value(self):
        assert ServiceType.SQS == "sqs"
        assert ServiceType.SQS.value == "sqs"

    def test_sns_from_string(self):
        assert ServiceType("sns") is ServiceType.SNS

    def test_sqs_from_string(self):
        assert ServiceType("sqs") is ServiceType.SQS

    def test_sns_resource_instance_accepted(self):
        """An SNS ResourceInstance can be created without errors."""
        resource = ResourceInstance(name="my-topic", service_type=ServiceType.SNS)
        assert resource.service_type == ServiceType.SNS

    def test_sqs_resource_instance_accepted(self):
        """An SQS ResourceInstance can be created without errors."""
        resource = ResourceInstance(name="my-queue", service_type=ServiceType.SQS)
        assert resource.service_type == ServiceType.SQS


# ===========================================================================
# 2. Connection model connection_config
# ===========================================================================

class TestConnectionConfig:
    """Test connection_config is optional and defaults to empty dict."""

    def test_connection_without_config_defaults_to_empty_dict(self):
        conn = Connection(source="a", target="b", connection_type="triggers")
        assert conn.connection_config == {}

    def test_connection_with_config(self):
        conn = Connection(
            source="a",
            target="b",
            connection_type="triggers",
            connection_config={"route_path": "/api"},
        )
        assert conn.connection_config == {"route_path": "/api"}

    def test_connection_config_with_mixed_value_types(self):
        conn = Connection(
            source="a",
            target="b",
            connection_type="triggers",
            connection_config={
                "route_path": "/api",
                "batch_size": 10,
                "enabled": True,
                "ratio": 0.5,
            },
        )
        assert conn.connection_config["route_path"] == "/api"
        assert conn.connection_config["batch_size"] == 10
        assert conn.connection_config["enabled"] is True
        assert conn.connection_config["ratio"] == 0.5


# ===========================================================================
# 3. ConnectionIR carries connection_config
# ===========================================================================

class TestConnectionIRConfig:
    """Test ConnectionIR model carries connection_config through."""

    def test_connection_ir_defaults_to_empty_dict(self):
        conn_ir = ConnectionIR(
            source_name="a",
            target_name="b",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.SNS,
            connection_type="publishes_to",
        )
        assert conn_ir.connection_config == {}

    def test_connection_ir_with_config(self):
        config = {"batch_size": 5, "route_path": "/events"}
        conn_ir = ConnectionIR(
            source_name="a",
            target_name="b",
            source_service=ServiceType.SQS,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config=config,
        )
        assert conn_ir.connection_config == config


# ===========================================================================
# 4. IR Builder accepts new compatible pairs
# ===========================================================================

class TestIRBuilderNewCompatiblePairs:
    """Test IR Builder accepts Lambda→SNS, Lambda→SQS, SQS→Lambda, SNS→SQS, SNS→Lambda."""

    def test_lambda_to_sns_accepted(self):
        desc = _make_input(
            resources=[_lambda_resource(), _sns_resource()],
            connections=[Connection(source="my-func", target="my-topic", connection_type="publishes_to")],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.connections) == 1
        assert ir.connections[0].source_service == ServiceType.LAMBDA
        assert ir.connections[0].target_service == ServiceType.SNS

    def test_lambda_to_sqs_accepted(self):
        desc = _make_input(
            resources=[_lambda_resource(), _sqs_resource()],
            connections=[Connection(source="my-func", target="my-queue", connection_type="sends_to")],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.connections) == 1
        assert ir.connections[0].source_service == ServiceType.LAMBDA
        assert ir.connections[0].target_service == ServiceType.SQS

    def test_sqs_to_lambda_accepted(self):
        desc = _make_input(
            resources=[_sqs_resource(), _lambda_resource()],
            connections=[Connection(source="my-queue", target="my-func", connection_type="triggers")],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.connections) == 1
        assert ir.connections[0].source_service == ServiceType.SQS
        assert ir.connections[0].target_service == ServiceType.LAMBDA

    def test_sns_to_sqs_accepted(self):
        desc = _make_input(
            resources=[_sns_resource(), _sqs_resource()],
            connections=[Connection(source="my-topic", target="my-queue", connection_type="delivers_to")],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.connections) == 1
        assert ir.connections[0].source_service == ServiceType.SNS
        assert ir.connections[0].target_service == ServiceType.SQS

    def test_sns_to_lambda_accepted(self):
        desc = _make_input(
            resources=[_sns_resource(), _lambda_resource()],
            connections=[Connection(source="my-topic", target="my-func", connection_type="triggers")],
        )
        ir = IRBuilder().build(desc)
        assert len(ir.connections) == 1
        assert ir.connections[0].source_service == ServiceType.SNS
        assert ir.connections[0].target_service == ServiceType.LAMBDA

    def test_connection_config_passes_through_ir_builder(self):
        """connection_config from input Connection flows into ConnectionIR."""
        config = {"batch_size": 20}
        desc = _make_input(
            resources=[_sqs_resource(), _lambda_resource()],
            connections=[
                Connection(
                    source="my-queue",
                    target="my-func",
                    connection_type="triggers",
                    connection_config=config,
                )
            ],
        )
        ir = IRBuilder().build(desc)
        assert ir.connections[0].connection_config == config


# ===========================================================================
# 5. IR Builder rejects unsupported pairs
# ===========================================================================

class TestIRBuilderRejectsUnsupportedPairs:
    """Test IR Builder rejects incompatible connection pairs with 422."""

    def test_sqs_to_sns_rejected(self):
        desc = _make_input(
            resources=[_sqs_resource(), _sns_resource()],
            connections=[Connection(source="my-queue", target="my-topic", connection_type="sends_to")],
        )
        with pytest.raises(HTTPException) as exc_info:
            IRBuilder().build(desc)
        assert exc_info.value.status_code == 422
        assert "Incompatible connection" in exc_info.value.detail

    def test_sns_to_sns_rejected(self):
        desc = _make_input(
            resources=[
                _sns_resource("topic-a"),
                _sns_resource("topic-b"),
            ],
            connections=[Connection(source="topic-a", target="topic-b", connection_type="forwards_to")],
        )
        with pytest.raises(HTTPException) as exc_info:
            IRBuilder().build(desc)
        assert exc_info.value.status_code == 422
        assert "Incompatible connection" in exc_info.value.detail

    def test_sqs_to_sqs_rejected(self):
        desc = _make_input(
            resources=[
                _sqs_resource("queue-a"),
                _sqs_resource("queue-b"),
            ],
            connections=[Connection(source="queue-a", target="queue-b", connection_type="forwards_to")],
        )
        with pytest.raises(HTTPException) as exc_info:
            IRBuilder().build(desc)
        assert exc_info.value.status_code == 422
        assert "Incompatible connection" in exc_info.value.detail

    def test_sns_to_s3_rejected(self):
        desc = _make_input(
            resources=[
                _sns_resource(),
                ResourceInstance(name="my-bucket", service_type=ServiceType.S3),
            ],
            connections=[Connection(source="my-topic", target="my-bucket", connection_type="delivers_to")],
        )
        with pytest.raises(HTTPException) as exc_info:
            IRBuilder().build(desc)
        assert exc_info.value.status_code == 422
        assert "Incompatible connection" in exc_info.value.detail

    def test_sqs_to_dynamodb_rejected(self):
        desc = _make_input(
            resources=[
                _sqs_resource(),
                ResourceInstance(
                    name="my-table",
                    service_type=ServiceType.DYNAMODB,
                    config=ResourceConfig(hash_key="id"),
                ),
            ],
            connections=[Connection(source="my-queue", target="my-table", connection_type="writes_to")],
        )
        with pytest.raises(HTTPException) as exc_info:
            IRBuilder().build(desc)
        assert exc_info.value.status_code == 422
        assert "Incompatible connection" in exc_info.value.detail


# ===========================================================================
# 6. _build_iam_resources for SNS and SQS
# ===========================================================================

class TestBuildIAMResources:
    """Test _build_iam_resources returns correct ARN references for SNS and SQS."""

    def test_sns_arn_reference(self):
        result = _build_iam_resources("my-topic", ServiceType.SNS)
        assert result == ["${aws_sns_topic.my-topic.arn}"]

    def test_sqs_arn_reference(self):
        result = _build_iam_resources("my-queue", ServiceType.SQS)
        assert result == ["${aws_sqs_queue.my-queue.arn}"]

    def test_sns_arn_with_different_name(self):
        result = _build_iam_resources("notifications", ServiceType.SNS)
        assert result == ["${aws_sns_topic.notifications.arn}"]

    def test_sqs_arn_with_different_name(self):
        result = _build_iam_resources("order-events", ServiceType.SQS)
        assert result == ["${aws_sqs_queue.order-events.arn}"]


# ===========================================================================
# 7. IAM statement derivation for new connection types
# ===========================================================================

class TestIAMStatementsForNewConnections:
    """Test IAM statements are correctly derived for Lambda→SNS and Lambda→SQS."""

    def test_lambda_to_sns_iam_statements(self):
        desc = _make_input(
            resources=[_lambda_resource(), _sns_resource()],
            connections=[Connection(source="my-func", target="my-topic", connection_type="publishes_to")],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(m for m in ir.modules if m.service_type == ServiceType.LAMBDA)
        func_ir = lambda_module.instances[0]
        assert len(func_ir.iam_statements) == 1
        stmt = func_ir.iam_statements[0]
        assert stmt.effect == "Allow"
        assert "sns:Publish" in stmt.actions
        assert "${aws_sns_topic.my-topic.arn}" in stmt.resources

    def test_lambda_to_sqs_iam_statements(self):
        desc = _make_input(
            resources=[_lambda_resource(), _sqs_resource()],
            connections=[Connection(source="my-func", target="my-queue", connection_type="sends_to")],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(m for m in ir.modules if m.service_type == ServiceType.LAMBDA)
        func_ir = lambda_module.instances[0]
        assert len(func_ir.iam_statements) == 1
        stmt = func_ir.iam_statements[0]
        assert stmt.effect == "Allow"
        assert "sqs:SendMessage" in stmt.actions
        assert "${aws_sqs_queue.my-queue.arn}" in stmt.resources

    def test_lambda_to_multiple_targets_produces_multiple_statements(self):
        desc = _make_input(
            resources=[_lambda_resource(), _sns_resource(), _sqs_resource()],
            connections=[
                Connection(source="my-func", target="my-topic", connection_type="publishes_to"),
                Connection(source="my-func", target="my-queue", connection_type="sends_to"),
            ],
        )
        ir = IRBuilder().build(desc)
        lambda_module = next(m for m in ir.modules if m.service_type == ServiceType.LAMBDA)
        func_ir = lambda_module.instances[0]
        assert len(func_ir.iam_statements) == 2
        actions = [a for stmt in func_ir.iam_statements for a in stmt.actions]
        assert "sns:Publish" in actions
        assert "sqs:SendMessage" in actions
