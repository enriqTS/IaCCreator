"""Backward compatibility tests for the API Gateway overhaul.

Verifies that existing configurations continue to produce identical output
after the generator expansion. Covers Requirements 12.1, 12.2, 12.3, 12.4.
"""

import pytest

from app.generators.api_gateway_generator import APIGatewayGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import (
    ConnectionIR,
    EnvironmentIR,
    GlobalTerraformConfigIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.connection_processor import ConnectionProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_instance(name: str, config: ResourceConfig) -> ResourceInstanceIR:
    """Create a ResourceInstanceIR for API Gateway testing."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.API_GATEWAY,
        config=config,
    )


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
# 1. ResourceConfig with only original fields produces identical HCL
#    (Requirement 12.1)
# ===========================================================================


class TestOriginalFieldsProduceIdenticalHCL:
    """ResourceConfig with only original 7 fields produces the same HCL as before overhaul."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_minimal_http_api_only_produces_api_resource(self):
        """Minimal HTTP config produces only the aws_apigatewayv2_api resource block."""
        config = ResourceConfig(protocol_type="HTTP")
        instance = _make_instance("my_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        # Should contain only the API resource block
        assert 'resource "aws_apigatewayv2_api" "my_api"' in hcl
        assert "protocol_type" in hcl

        # Should NOT contain any new resource types
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl
        assert "aws_apigatewayv2_authorizer" not in hcl
        assert "aws_apigatewayv2_domain_name" not in hcl
        assert "aws_apigatewayv2_api_mapping" not in hcl
        assert "aws_apigatewayv2_vpc_link" not in hcl
        assert "aws_apigatewayv2_integration" not in hcl
        assert "aws_apigatewayv2_api_key" not in hcl

    def test_http_api_with_description(self):
        """HTTP API with description produces only the API resource with description."""
        config = ResourceConfig(protocol_type="HTTP", description="My API")
        instance = _make_instance("my_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_api" "my_api"' in hcl
        assert "var.description" in hcl
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl

    def test_http_api_with_cors_configuration(self):
        """HTTP API with cors_configuration produces only the API resource with CORS."""
        config = ResourceConfig(
            protocol_type="HTTP",
            cors_configuration={"allow_origins": ["*"]},
        )
        instance = _make_instance("my_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_api" "my_api"' in hcl
        assert "var.cors_configuration" in hcl
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl

    def test_http_api_with_disable_execute_api_endpoint(self):
        """HTTP API with disable_execute_api_endpoint produces only the API resource."""
        config = ResourceConfig(
            protocol_type="HTTP",
            disable_execute_api_endpoint=True,
        )
        instance = _make_instance("my_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_api" "my_api"' in hcl
        assert "var.disable_execute_api_endpoint" in hcl
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl

    def test_websocket_api_with_route_selection_expression(self):
        """WebSocket API with route_selection_expression produces only the API resource."""
        config = ResourceConfig(
            protocol_type="WEBSOCKET",
            route_selection_expression="$request.body.action",
        )
        instance = _make_instance("ws_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_api" "ws_api"' in hcl
        assert "var.route_selection_expression" in hcl
        # No extra resources generated
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl
        assert "aws_apigatewayv2_authorizer" not in hcl

    def test_http_api_with_tags(self):
        """HTTP API with tags produces only the API resource with tags."""
        config = ResourceConfig(
            protocol_type="HTTP",
            tags={"env": "dev", "team": "backend"},
        )
        instance = _make_instance("my_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_api" "my_api"' in hcl
        assert "var.tags" in hcl
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl

    def test_full_original_config_produces_only_api_resource(self):
        """Config with ALL original fields produces only the API resource block."""
        config = ResourceConfig(
            protocol_type="HTTP",
            description="Full API",
            cors_configuration={"allow_origins": ["https://example.com"]},
            disable_execute_api_endpoint=False,
            tags={"project": "test"},
        )
        instance = _make_instance("full_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        # Only the API resource block should be present
        assert hcl.count('resource "') == 1
        assert 'resource "aws_apigatewayv2_api" "full_api"' in hcl


# ===========================================================================
# 2. New fields set to None produce identical output to absent fields
#    (Requirement 12.2, 12.4)
# ===========================================================================


class TestNoneFieldsProduceIdenticalOutput:
    """When all new fields are None, generate_resource_tf produces only the API resource."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_explicit_none_fields_match_absent_fields(self):
        """Explicitly setting new fields to None produces same output as not setting them."""
        # Config without new fields
        config_minimal = ResourceConfig(protocol_type="HTTP", description="Test API")
        instance_minimal = _make_instance("api", config_minimal)
        hcl_minimal = self.gen.generate_resource_tf(instance_minimal)

        # Config with all new fields explicitly set to None
        config_explicit = ResourceConfig(
            protocol_type="HTTP",
            description="Test API",
            routes=None,
            stages=None,
            authorizers=None,
            custom_domain=None,
            vpc_links=None,
            integrations=None,
            api_key_required=None,
            throttling_burst_limit=None,
            throttling_rate_limit=None,
            access_log_retention_days=None,
            access_log_format=None,
        )
        instance_explicit = _make_instance("api", config_explicit)
        hcl_explicit = self.gen.generate_resource_tf(instance_explicit)

        # Byte-for-byte identical
        assert hcl_minimal == hcl_explicit

    def test_none_routes_no_route_resources(self):
        """routes=None produces no aws_apigatewayv2_route resources."""
        config = ResourceConfig(protocol_type="HTTP", routes=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_route" not in hcl

    def test_none_stages_no_stage_resources(self):
        """stages=None produces no aws_apigatewayv2_stage resources."""
        config = ResourceConfig(protocol_type="HTTP", stages=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_stage" not in hcl

    def test_none_authorizers_no_authorizer_resources(self):
        """authorizers=None produces no aws_apigatewayv2_authorizer resources."""
        config = ResourceConfig(protocol_type="HTTP", authorizers=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_authorizer" not in hcl

    def test_none_custom_domain_no_domain_resources(self):
        """custom_domain=None produces no domain or api_mapping resources."""
        config = ResourceConfig(protocol_type="HTTP", custom_domain=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_domain_name" not in hcl
        assert "aws_apigatewayv2_api_mapping" not in hcl

    def test_none_vpc_links_no_vpc_link_resources(self):
        """vpc_links=None produces no aws_apigatewayv2_vpc_link resources."""
        config = ResourceConfig(protocol_type="HTTP", vpc_links=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_vpc_link" not in hcl

    def test_none_integrations_no_integration_resources(self):
        """integrations=None produces no aws_apigatewayv2_integration resources."""
        config = ResourceConfig(protocol_type="HTTP", integrations=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_integration" not in hcl

    def test_none_api_key_no_key_expression(self):
        """api_key_required=None produces no api_key_selection_expression."""
        config = ResourceConfig(protocol_type="HTTP", api_key_required=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "api_key_selection_expression" not in hcl
        assert "aws_apigatewayv2_api_key" not in hcl

    def test_variables_tf_with_none_fields_matches_minimal(self):
        """generate_variables_tf with None fields matches minimal config output."""
        config_minimal = ResourceConfig(protocol_type="HTTP")
        instance_minimal = _make_instance("api", config_minimal)
        vars_minimal = self.gen.generate_variables_tf(instance_minimal)

        config_explicit = ResourceConfig(
            protocol_type="HTTP",
            routes=None,
            stages=None,
            authorizers=None,
            custom_domain=None,
            vpc_links=None,
            integrations=None,
            api_key_required=None,
        )
        instance_explicit = _make_instance("api", config_explicit)
        vars_explicit = self.gen.generate_variables_tf(instance_explicit)

        assert vars_minimal == vars_explicit


# ===========================================================================
# 3. ConnectionProcessor with original connection_config keys produces
#    identical output (Requirement 12.3)
# ===========================================================================


class TestConnectionProcessorBackwardCompat:
    """ConnectionProcessor with original connection_config keys produces identical output."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _make_apigw_lambda_project(self, connection_config: dict):
        """Create a project with APIGW→Lambda connection."""
        apigw = ResourceInstanceIR(
            name="my_api",
            service_type=ServiceType.API_GATEWAY,
            config=ResourceConfig(protocol_type="HTTP"),
        )
        func = ResourceInstanceIR(
            name="my_func",
            service_type=ServiceType.LAMBDA,
            config=ResourceConfig(handler="index.handler", runtime="python3.12"),
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

    def test_empty_config_produces_default_integration(self):
        """Empty connection_config produces default AWS_PROXY integration."""
        conn, project = self._make_apigw_lambda_project({})
        files = self.processor.process(conn, project)

        assert len(files) == 3
        integration_file = next(f for f in files if "integration_" in f.path)
        assert "AWS_PROXY" in integration_file.content
        assert "aws_lambda_function.my_func.invoke_arn" in integration_file.content

    def test_original_keys_route_path_and_http_method(self):
        """connection_config with route_path and http_method produces correct route."""
        conn, project = self._make_apigw_lambda_project(
            {"route_path": "/users", "http_method": "GET"}
        )
        files = self.processor.process(conn, project)

        route_file = next(f for f in files if "route_" in f.path)
        assert 'route_key = "GET /users"' in route_file.content

    def test_original_keys_produce_three_files(self):
        """Original keys produce exactly 3 files: integration, route, permission."""
        conn, project = self._make_apigw_lambda_project(
            {"route_path": "/items", "http_method": "POST"}
        )
        files = self.processor.process(conn, project)

        assert len(files) == 3
        paths = [f.path for f in files]
        assert any("integration_my_func.tf" in p for p in paths)
        assert any("route_my_func.tf" in p for p in paths)
        assert any("permission_my_func.tf" in p for p in paths)

    def test_original_keys_file_paths_unchanged(self):
        """File paths follow the categorized pattern: modules/networking/api-gateway/{source}/..."""
        conn, project = self._make_apigw_lambda_project(
            {"route_path": "/data", "http_method": "DELETE"}
        )
        files = self.processor.process(conn, project)

        paths = [f.path for f in files]
        assert "test-project/modules/networking/api-gateway/my_api/integration_my_func.tf" in paths
        assert "test-project/modules/networking/api-gateway/my_api/route_my_func.tf" in paths
        assert "test-project/modules/networking/api-gateway/my_api/permission_my_func.tf" in paths

    def test_permission_file_content_unchanged(self):
        """Permission file has the same structure with original keys."""
        conn, project = self._make_apigw_lambda_project(
            {"route_path": "/test", "http_method": "GET"}
        )
        files = self.processor.process(conn, project)

        perm_file = next(f for f in files if "permission_" in f.path)
        assert 'resource "aws_lambda_permission"' in perm_file.content
        assert "lambda:InvokeFunction" in perm_file.content
        assert "apigateway.amazonaws.com" in perm_file.content
        assert "aws_lambda_function.my_func.function_name" in perm_file.content
        assert "aws_apigatewayv2_api.my_api.execution_arn" in perm_file.content

    def test_integration_defaults_match_original_behavior(self):
        """Default integration_type (AWS_PROXY) and payload_format_version (2.0) match original."""
        conn, project = self._make_apigw_lambda_project({})
        files = self.processor.process(conn, project)

        integration_file = next(f for f in files if "integration_" in f.path)
        assert "AWS_PROXY" in integration_file.content
        assert '"2.0"' in integration_file.content
        # No VPC link attributes when not specified
        assert "VPC_LINK" not in integration_file.content
        assert "connection_id" not in integration_file.content


# ===========================================================================
# 4. Byte-for-byte comparison between configs with defaults vs absent fields
#    (Requirement 12.4)
# ===========================================================================


class TestByteForByteIdenticalOutput:
    """Setting new fields to default values produces identical output to absent fields."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_resource_tf_byte_identical(self):
        """generate_resource_tf output is byte-for-byte identical with/without None fields."""
        config_without = ResourceConfig(
            protocol_type="HTTP",
            description="API",
            cors_configuration={"allow_origins": ["*"]},
            disable_execute_api_endpoint=True,
            tags={"env": "prod"},
        )
        config_with_defaults = ResourceConfig(
            protocol_type="HTTP",
            description="API",
            cors_configuration={"allow_origins": ["*"]},
            disable_execute_api_endpoint=True,
            tags={"env": "prod"},
            # All new fields at their defaults (None)
            routes=None,
            stages=None,
            authorizers=None,
            custom_domain=None,
            vpc_links=None,
            integrations=None,
            api_key_required=None,
            throttling_burst_limit=None,
            throttling_rate_limit=None,
            access_log_retention_days=None,
            access_log_format=None,
        )

        instance_without = _make_instance("api", config_without)
        instance_with = _make_instance("api", config_with_defaults)

        hcl_without = self.gen.generate_resource_tf(instance_without)
        hcl_with = self.gen.generate_resource_tf(instance_with)

        assert hcl_without == hcl_with
        # Verify it's actually the same bytes
        assert hcl_without.encode("utf-8") == hcl_with.encode("utf-8")

    def test_variables_tf_byte_identical(self):
        """generate_variables_tf output is byte-for-byte identical with/without None fields."""
        config_without = ResourceConfig(
            protocol_type="HTTP",
            description="API",
            tags={"env": "prod"},
        )
        config_with_defaults = ResourceConfig(
            protocol_type="HTTP",
            description="API",
            tags={"env": "prod"},
            routes=None,
            stages=None,
            authorizers=None,
            custom_domain=None,
            vpc_links=None,
            integrations=None,
            api_key_required=None,
        )

        instance_without = _make_instance("api", config_without)
        instance_with = _make_instance("api", config_with_defaults)

        vars_without = self.gen.generate_variables_tf(instance_without)
        vars_with = self.gen.generate_variables_tf(instance_with)

        assert vars_without == vars_with
        assert vars_without.encode("utf-8") == vars_with.encode("utf-8")

    def test_outputs_tf_byte_identical(self):
        """generate_outputs_tf output is byte-for-byte identical with/without None fields."""
        config_without = ResourceConfig(protocol_type="HTTP")
        config_with_defaults = ResourceConfig(
            protocol_type="HTTP",
            routes=None,
            stages=None,
            authorizers=None,
            custom_domain=None,
            vpc_links=None,
            integrations=None,
            api_key_required=None,
        )

        instance_without = _make_instance("api", config_without)
        instance_with = _make_instance("api", config_with_defaults)

        outputs_without = self.gen.generate_outputs_tf(instance_without)
        outputs_with = self.gen.generate_outputs_tf(instance_with)

        assert outputs_without == outputs_with
        assert outputs_without.encode("utf-8") == outputs_with.encode("utf-8")

    def test_connection_processor_byte_identical(self):
        """ConnectionProcessor output is byte-for-byte identical with original keys only."""
        processor = ConnectionProcessor()

        # Connection with empty config (original behavior)
        apigw = ResourceInstanceIR(
            name="api",
            service_type=ServiceType.API_GATEWAY,
            config=ResourceConfig(protocol_type="HTTP"),
        )
        func = ResourceInstanceIR(
            name="func",
            service_type=ServiceType.LAMBDA,
            config=ResourceConfig(handler="index.handler", runtime="python3.12"),
        )

        conn_empty = ConnectionIR(
            source_name="api",
            target_name="func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config={},
        )
        project_empty = _make_project([apigw, func], [conn_empty])
        files_empty = processor.process(conn_empty, project_empty)

        # Connection with only original keys (route_path, http_method)
        # Using the same defaults that the processor would use
        conn_original = ConnectionIR(
            source_name="api",
            target_name="func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config={"route_path": "/$default", "http_method": "ANY"},
        )
        # Need fresh instances since IAM statements are mutated in place
        apigw2 = ResourceInstanceIR(
            name="api",
            service_type=ServiceType.API_GATEWAY,
            config=ResourceConfig(protocol_type="HTTP"),
        )
        func2 = ResourceInstanceIR(
            name="func",
            service_type=ServiceType.LAMBDA,
            config=ResourceConfig(handler="index.handler", runtime="python3.12"),
        )
        project_original = _make_project([apigw2, func2], [conn_original])
        files_original = processor.process(conn_original, project_original)

        # Same number of files
        assert len(files_empty) == len(files_original)

        # Same file paths
        paths_empty = sorted(f.path for f in files_empty)
        paths_original = sorted(f.path for f in files_original)
        assert paths_empty == paths_original

        # Same content for each file
        for f_empty, f_original in zip(
            sorted(files_empty, key=lambda f: f.path),
            sorted(files_original, key=lambda f: f.path),
        ):
            assert f_empty.content == f_original.content
