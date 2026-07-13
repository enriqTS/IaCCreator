"""Tests for the API Gateway generator and connection handler.

Verifies that API Gateway generator produces correct HCL and that the
APIGW→Lambda handler via process_all generates the expected files.
Covers Requirements 12.1, 12.2, 12.3, 12.4.
"""


from app.generators.api_gateway_generator import APIGatewayGenerator
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
from app.services.connection_processor import ConnectionProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_instance(name: str, config: ApiGatewayConfig) -> ResourceInstanceIR:
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
# 1. ApiGatewayConfig with only original fields produces identical HCL
#    (Requirement 12.1)
# ===========================================================================


class TestOriginalFieldsProduceIdenticalHCL:
    """ApiGatewayConfig with only original 7 fields produces the same HCL as before overhaul."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_minimal_http_api_only_produces_api_resource(self):
        """Minimal HTTP config produces only the aws_apigatewayv2_api resource block."""
        config = ApiGatewayConfig(api_name="my_api", protocol_type="HTTP")
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
        config = ApiGatewayConfig(api_name="my_api", protocol_type="HTTP", description="My API")
        instance = _make_instance("my_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_api" "my_api"' in hcl
        assert "var.description" in hcl
        assert "aws_apigatewayv2_route" not in hcl
        assert "aws_apigatewayv2_stage" not in hcl

    def test_http_api_with_cors_configuration(self):
        """HTTP API with cors_configuration produces only the API resource with CORS."""
        config = ApiGatewayConfig(api_name="test-api",
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
        config = ApiGatewayConfig(api_name="test-api",
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
        config = ApiGatewayConfig(api_name="test-api",
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
        config = ApiGatewayConfig(api_name="test-api",
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
        config = ApiGatewayConfig(api_name="test-api",
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
        config_minimal = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", description="Test API")
        instance_minimal = _make_instance("api", config_minimal)
        hcl_minimal = self.gen.generate_resource_tf(instance_minimal)

        # Config with all new fields explicitly set to None
        config_explicit = ApiGatewayConfig(api_name="test-api",
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
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", routes=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_route" not in hcl

    def test_none_stages_no_stage_resources(self):
        """stages=None produces no aws_apigatewayv2_stage resources."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", stages=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_stage" not in hcl

    def test_none_authorizers_no_authorizer_resources(self):
        """authorizers=None produces no aws_apigatewayv2_authorizer resources."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", authorizers=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_authorizer" not in hcl

    def test_none_custom_domain_no_domain_resources(self):
        """custom_domain=None produces no domain or api_mapping resources."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", custom_domain=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_domain_name" not in hcl
        assert "aws_apigatewayv2_api_mapping" not in hcl

    def test_none_vpc_links_no_vpc_link_resources(self):
        """vpc_links=None produces no aws_apigatewayv2_vpc_link resources."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", vpc_links=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_vpc_link" not in hcl

    def test_none_integrations_no_integration_resources(self):
        """integrations=None produces no aws_apigatewayv2_integration resources."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", integrations=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "aws_apigatewayv2_integration" not in hcl

    def test_none_api_key_no_key_expression(self):
        """api_key_required=None produces no api_key_selection_expression."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP", api_key_required=None)
        instance = _make_instance("api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "api_key_selection_expression" not in hcl
        assert "aws_apigatewayv2_api_key" not in hcl

    def test_variables_tf_with_none_fields_matches_minimal(self):
        """generate_variables_tf with None fields matches minimal config output."""
        config_minimal = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP")
        instance_minimal = _make_instance("api", config_minimal)
        vars_minimal = self.gen.generate_variables_tf(instance_minimal)

        config_explicit = ApiGatewayConfig(api_name="test-api",
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
# 3. ConnectionProcessor with routes array format produces correct output
#    (Requirement 12.3)
# ===========================================================================


class TestConnectionProcessorWithRoutes:
    """ConnectionProcessor with routes array format produces correct output."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _make_apigw_lambda_project(self, connection_config: dict):
        """Create a project with APIGW→Lambda connection."""
        apigw = ResourceInstanceIR(
            name="my_api",
            service_type=ServiceType.API_GATEWAY,
            config=ApiGatewayConfig(api_name="test-api", protocol_type="HTTP"),
        )
        func = ResourceInstanceIR(
            name="my_func",
            service_type=ServiceType.LAMBDA,
            config=LambdaConfig(function_name="my-func", handler="index.handler", runtime="python3.12"),
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
        return project

    def test_empty_routes_produces_integration_and_permission(self):
        """Empty routes list produces 2 files: integration + permission (no route)."""
        project = self._make_apigw_lambda_project({"routes": []})
        files = self.processor.process_all(project)

        assert len(files) == 2
        integration_file = next(f for f in files if "integration_" in f.path)
        assert "AWS_PROXY" in integration_file.content
        assert "aws_lambda_function.my_func.invoke_arn" in integration_file.content

    def test_single_route_produces_three_files(self):
        """Single route produces exactly 3 files: integration, route, permission."""
        project = self._make_apigw_lambda_project(
            {"routes": [{"methods": ["GET"], "path": "/users"}]}
        )
        files = self.processor.process_all(project)

        assert len(files) == 3
        paths = [f.path for f in files]
        assert any("integration_my_func.tf" in p for p in paths)
        assert any("route_my_func" in p for p in paths)
        assert any("permission_my_func.tf" in p for p in paths)

    def test_route_key_uses_method_and_path(self):
        """Route resource has correct route_key from method and path."""
        project = self._make_apigw_lambda_project(
            {"routes": [{"methods": ["GET"], "path": "/users"}]}
        )
        files = self.processor.process_all(project)

        route_file = next(f for f in files if "route_" in f.path)
        assert 'route_key = "GET /users"' in route_file.content

    def test_file_paths_follow_categorized_pattern(self):
        """File paths follow the categorized pattern: modules/networking/api-gateway/{source}/..."""
        project = self._make_apigw_lambda_project(
            {"routes": [{"methods": ["DELETE"], "path": "/data"}]}
        )
        files = self.processor.process_all(project)

        paths = [f.path for f in files]
        assert any(
            "test-project/modules/networking/api-gateway/my_api/integration_my_func.tf" in p
            for p in paths
        )
        assert any(
            "test-project/modules/networking/api-gateway/my_api/permission_my_func.tf" in p
            for p in paths
        )

    def test_permission_file_content(self):
        """Permission file has the same structure."""
        project = self._make_apigw_lambda_project(
            {"routes": [{"methods": ["GET"], "path": "/test"}]}
        )
        files = self.processor.process_all(project)

        perm_file = next(f for f in files if "permission_" in f.path)
        assert 'resource "aws_lambda_permission"' in perm_file.content
        assert "lambda:InvokeFunction" in perm_file.content
        assert "apigateway.amazonaws.com" in perm_file.content
        assert "aws_lambda_function.my_func.function_name" in perm_file.content
        assert "aws_apigatewayv2_api.my_api.execution_arn" in perm_file.content

    def test_integration_defaults_match_expected(self):
        """Default integration_type (AWS_PROXY) and payload_format_version (2.0)."""
        project = self._make_apigw_lambda_project({"routes": []})
        files = self.processor.process_all(project)

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
        config_without = ApiGatewayConfig(api_name="test-api",
            protocol_type="HTTP",
            description="API",
            cors_configuration={"allow_origins": ["*"]},
            disable_execute_api_endpoint=True,
            tags={"env": "prod"},
        )
        config_with_defaults = ApiGatewayConfig(api_name="test-api",
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
        config_without = ApiGatewayConfig(api_name="test-api",
            protocol_type="HTTP",
            description="API",
            tags={"env": "prod"},
        )
        config_with_defaults = ApiGatewayConfig(api_name="test-api",
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
        config_without = ApiGatewayConfig(api_name="test-api", protocol_type="HTTP")
        config_with_defaults = ApiGatewayConfig(api_name="test-api",
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

    def test_connection_processor_single_route(self):
        """ConnectionProcessor with single route produces consistent output."""
        processor = ConnectionProcessor()

        apigw = ResourceInstanceIR(
            name="api",
            service_type=ServiceType.API_GATEWAY,
            config=ApiGatewayConfig(api_name="test-api", protocol_type="HTTP"),
        )
        func = ResourceInstanceIR(
            name="func",
            service_type=ServiceType.LAMBDA,
            config=LambdaConfig(function_name="my-func", handler="index.handler", runtime="python3.12"),
        )

        conn = ConnectionIR(
            source_name="api",
            target_name="func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config={"routes": [{"methods": ["GET"], "path": "/users"}]},
        )
        project = _make_project([apigw, func], [conn])
        files = processor.process_all(project)

        # 3 files: integration, route, permission
        assert len(files) == 3

        # Verify file paths
        paths = sorted(f.path for f in files)
        assert any("integration_func.tf" in p for p in paths)
        assert any("route_func" in p for p in paths)
        assert any("permission_func.tf" in p for p in paths)

        # Second run produces identical output
        apigw2 = ResourceInstanceIR(
            name="api",
            service_type=ServiceType.API_GATEWAY,
            config=ApiGatewayConfig(api_name="test-api", protocol_type="HTTP"),
        )
        func2 = ResourceInstanceIR(
            name="func",
            service_type=ServiceType.LAMBDA,
            config=LambdaConfig(function_name="my-func", handler="index.handler", runtime="python3.12"),
        )
        conn2 = ConnectionIR(
            source_name="api",
            target_name="func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config={"routes": [{"methods": ["GET"], "path": "/users"}]},
        )
        project2 = _make_project([apigw2, func2], [conn2])
        files2 = processor.process_all(project2)

        # Same number of files
        assert len(files) == len(files2)

        # Same file paths
        paths2 = sorted(f.path for f in files2)
        assert paths == paths2

        # Same content for each file
        for f1, f2 in zip(
            sorted(files, key=lambda f: f.path),
            sorted(files2, key=lambda f: f.path),
        ):
            assert f1.content == f2.content
