"""Tests for the connection handler registry and ConnectionProcessor dispatch.

Covers:
- Registry completeness (all 9 entries exist)
- Unregistered connection type warning
- Multi-route tests for ApiGatewayLambdaHandler (single, multiple, path parameters)
"""

import logging

from app.models.input_models import ServiceType
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.ir_models import (
    ConnectionIR,
    EnvironmentIR,
    GlobalTerraformConfigIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.connection_handlers.apigw_lambda import ApiGatewayLambdaHandler
from app.services.connection_handlers.registry import CONNECTION_HANDLER_REGISTRY
from app.services.connection_processor import ConnectionProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(
    instances: list[ResourceInstanceIR],
    connections: list[ConnectionIR],
    project_name: str = "test-project",
) -> ProjectIR:
    """Build a minimal ProjectIR grouping instances by service type."""
    modules_map: dict[ServiceType, list[ResourceInstanceIR]] = {}
    for inst in instances:
        modules_map.setdefault(inst.service_type, []).append(inst)

    modules = [
        ServiceModuleIR(service_type=svc, instances=insts)
        for svc, insts in modules_map.items()
    ]

    return ProjectIR(
        project_name=project_name,
        environments=[EnvironmentIR(name="dev", variables={}, module_refs=[])],
        modules=modules,
        connections=connections,
        global_config=GlobalTerraformConfigIR(),
    )


# ===========================================================================
# 1. Registry Completeness
# ===========================================================================


class TestRegistryCompleteness:
    """Verify CONNECTION_HANDLER_REGISTRY contains all 9 expected entries."""

    def test_registry_has_nine_entries(self):
        """Registry must contain exactly 9 connection type pairs."""
        assert len(CONNECTION_HANDLER_REGISTRY) == 9

    def test_apigw_lambda_registered(self):
        """API_GATEWAY → LAMBDA is registered."""
        assert (ServiceType.API_GATEWAY, ServiceType.LAMBDA) in CONNECTION_HANDLER_REGISTRY

    def test_lambda_dynamodb_registered(self):
        """LAMBDA → DYNAMODB is registered."""
        assert (ServiceType.LAMBDA, ServiceType.DYNAMODB) in CONNECTION_HANDLER_REGISTRY

    def test_lambda_s3_registered(self):
        """LAMBDA → S3 is registered."""
        assert (ServiceType.LAMBDA, ServiceType.S3) in CONNECTION_HANDLER_REGISTRY

    def test_lambda_cloudwatch_registered(self):
        """LAMBDA → CLOUDWATCH is registered."""
        assert (ServiceType.LAMBDA, ServiceType.CLOUDWATCH) in CONNECTION_HANDLER_REGISTRY

    def test_lambda_sns_registered(self):
        """LAMBDA → SNS is registered."""
        assert (ServiceType.LAMBDA, ServiceType.SNS) in CONNECTION_HANDLER_REGISTRY

    def test_lambda_sqs_registered(self):
        """LAMBDA → SQS is registered."""
        assert (ServiceType.LAMBDA, ServiceType.SQS) in CONNECTION_HANDLER_REGISTRY

    def test_sqs_lambda_registered(self):
        """SQS → LAMBDA is registered."""
        assert (ServiceType.SQS, ServiceType.LAMBDA) in CONNECTION_HANDLER_REGISTRY

    def test_sns_sqs_registered(self):
        """SNS → SQS is registered."""
        assert (ServiceType.SNS, ServiceType.SQS) in CONNECTION_HANDLER_REGISTRY

    def test_sns_lambda_registered(self):
        """SNS → LAMBDA is registered."""
        assert (ServiceType.SNS, ServiceType.LAMBDA) in CONNECTION_HANDLER_REGISTRY


# ===========================================================================
# 2. Unregistered Connection Type Warning
# ===========================================================================


class TestUnregisteredConnectionTypeWarning:
    """Verify that unregistered connection types log a warning and produce no output."""

    def test_unregistered_pair_logs_warning(self, caplog):
        """An unregistered pair (S3→S3) logs a warning."""
        processor = ConnectionProcessor()

        s3_source = ResourceInstanceIR(
            name="bucket-a",
            service_type=ServiceType.S3,
            config=ApiGatewayConfig(api_name="dummy", protocol_type="HTTP"),
        )
        s3_target = ResourceInstanceIR(
            name="bucket-b",
            service_type=ServiceType.S3,
            config=ApiGatewayConfig(api_name="dummy", protocol_type="HTTP"),
        )
        conn = ConnectionIR(
            source_name="bucket-a",
            target_name="bucket-b",
            source_service=ServiceType.S3,
            target_service=ServiceType.S3,
            connection_type="replicates_to",
        )
        project = _make_project([s3_source, s3_target], [conn])

        with caplog.at_level(logging.WARNING):
            files = processor.process_all(project)

        assert files == []
        assert "No handler registered" in caplog.text
        assert "s3" in caplog.text.lower()

    def test_unregistered_pair_returns_empty_list(self):
        """An unregistered pair returns an empty list of generated files."""
        processor = ConnectionProcessor()

        s3_source = ResourceInstanceIR(
            name="bucket-a",
            service_type=ServiceType.S3,
            config=ApiGatewayConfig(api_name="dummy", protocol_type="HTTP"),
        )
        s3_target = ResourceInstanceIR(
            name="bucket-b",
            service_type=ServiceType.S3,
            config=ApiGatewayConfig(api_name="dummy", protocol_type="HTTP"),
        )
        conn = ConnectionIR(
            source_name="bucket-a",
            target_name="bucket-b",
            source_service=ServiceType.S3,
            target_service=ServiceType.S3,
            connection_type="replicates_to",
        )
        project = _make_project([s3_source, s3_target], [conn])
        files = processor.process_all(project)

        assert files == []


# ===========================================================================
# 3. Multi-Route Tests for ApiGatewayLambdaHandler
# ===========================================================================


class TestMultiRoute:
    """Test ApiGatewayLambdaHandler with various route configurations."""

    def setup_method(self):
        self.handler = ApiGatewayLambdaHandler()

    def _make_connection(self, connection_config: dict) -> tuple[ConnectionIR, ProjectIR]:
        """Create APIGW→Lambda connection with given config."""
        apigw = ResourceInstanceIR(
            name="my_api",
            service_type=ServiceType.API_GATEWAY,
            config=ApiGatewayConfig(api_name="my-api", protocol_type="HTTP"),
        )
        func = ResourceInstanceIR(
            name="my_func",
            service_type=ServiceType.LAMBDA,
            config=LambdaConfig(
                function_name="my-func", handler="index.handler", runtime="python3.12"
            ),
        )
        conn = ConnectionIR(
            source_name="my_api",
            target_name="my_func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config=connection_config,
        )
        project = _make_project([apigw, func], [conn])
        return conn, project

    def test_single_route_file_count(self):
        """Single route produces 3 files (integration + 1 route + permission)."""
        conn, project = self._make_connection(
            {"routes": [{"method": "GET", "path": "/users"}]}
        )
        files = self.handler.handle(conn, project)
        assert len(files) == 3

    def test_single_route_has_correct_route_key(self):
        """Single route has the expected route_key."""
        conn, project = self._make_connection(
            {"routes": [{"method": "GET", "path": "/users"}]}
        )
        files = self.handler.handle(conn, project)
        route_file = next(f for f in files if "route_" in f.path)
        assert 'route_key = "GET /users"' in route_file.content

    def test_multiple_routes_file_count(self):
        """Two routes produce 4 files (integration + 2 routes + permission)."""
        conn, project = self._make_connection(
            {
                "routes": [
                    {"method": "GET", "path": "/users"},
                    {"method": "POST", "path": "/users"},
                ]
            }
        )
        files = self.handler.handle(conn, project)
        assert len(files) == 4

    def test_multiple_routes_each_has_distinct_route_key(self):
        """Each route file has a distinct route_key."""
        conn, project = self._make_connection(
            {
                "routes": [
                    {"method": "GET", "path": "/users"},
                    {"method": "POST", "path": "/users"},
                ]
            }
        )
        files = self.handler.handle(conn, project)
        route_files = [f for f in files if "route_" in f.path]
        assert len(route_files) == 2

        route_keys = []
        for rf in route_files:
            if "GET /users" in rf.content:
                route_keys.append("GET /users")
            if "POST /users" in rf.content:
                route_keys.append("POST /users")
        assert "GET /users" in route_keys
        assert "POST /users" in route_keys

    def test_multiple_routes_single_integration(self):
        """Multiple routes still share a single integration file."""
        conn, project = self._make_connection(
            {
                "routes": [
                    {"method": "GET", "path": "/users"},
                    {"method": "POST", "path": "/users"},
                ]
            }
        )
        files = self.handler.handle(conn, project)
        integration_files = [f for f in files if "integration_" in f.path]
        assert len(integration_files) == 1

    def test_multiple_routes_single_permission(self):
        """Multiple routes still share a single permission file."""
        conn, project = self._make_connection(
            {
                "routes": [
                    {"method": "GET", "path": "/users"},
                    {"method": "POST", "path": "/users"},
                ]
            }
        )
        files = self.handler.handle(conn, project)
        permission_files = [f for f in files if "permission_" in f.path]
        assert len(permission_files) == 1

    def test_path_parameters_sanitized_in_name(self):
        """Path parameters {id} are sanitized to produce valid resource names."""
        conn, project = self._make_connection(
            {"routes": [{"method": "GET", "path": "/users/{id}"}]}
        )
        files = self.handler.handle(conn, project)
        route_file = next(f for f in files if "route_" in f.path)

        # The route_key should still contain the original path
        assert 'route_key = "GET /users/{id}"' in route_file.content

        # The file path should have the sanitized version (no braces or slashes)
        assert "{" not in route_file.path
        assert "}" not in route_file.path
        # Should contain the sanitized path segment
        assert "users_id" in route_file.path

    def test_path_parameters_resource_name_sanitized(self):
        """Terraform resource name for path with params is properly sanitized."""
        conn, project = self._make_connection(
            {"routes": [{"method": "GET", "path": "/users/{id}"}]}
        )
        files = self.handler.handle(conn, project)
        route_file = next(f for f in files if "route_" in f.path)

        # Resource name should be sanitized (no braces/slashes, underscores collapsed)
        assert "my_api_my_func_route_get_users_id" in route_file.content

    def test_three_routes_file_count(self):
        """Three routes produce 5 files (integration + 3 routes + permission)."""
        conn, project = self._make_connection(
            {
                "routes": [
                    {"method": "GET", "path": "/users"},
                    {"method": "POST", "path": "/users"},
                    {"method": "GET", "path": "/users/{id}"},
                ]
            }
        )
        files = self.handler.handle(conn, project)
        assert len(files) == 5
