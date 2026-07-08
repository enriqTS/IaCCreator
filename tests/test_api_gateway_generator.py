"""Unit tests for API Gateway generator new fields.

Tests the emission of new TerraformField-annotated attributes in the
API Gateway generator sub-resources: stages, authorizers, integrations,
custom domain, and routes.

Requirements: 4.9, 4.10, 4.11, 4.12, 4.13
"""

from app.generators.api_gateway_generator import APIGatewayGenerator
from app.models.input_models import ServiceType
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


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


# ===========================================================================
# Test stage access log settings emission (Requirement 4.9)
# ===========================================================================


class TestStageAccessLogSettings:
    """Stage fields produce access_log_settings in aws_apigatewayv2_stage."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_access_log_destination_arn_emits_access_log_settings(self):
        """When access_log_destination_arn is set, stage emits access_log_settings block."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            stages=[
                {
                    "name": "$default",
                    "auto_deploy": True,
                    "access_logging_enabled": True,
                }
            ],
            access_log_destination_arn="arn:aws:logs:us-east-1:123456789012:log-group:/test",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "access_log_settings" in hcl
        assert "var.access_log_destination_arn" in hcl

    def test_access_log_format_used_in_stage(self):
        """Custom access_log_format is emitted in the stage access_log_settings."""
        custom_format = '{"request":"$context.requestId"}'
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            stages=[
                {
                    "name": "$default",
                    "auto_deploy": True,
                    "access_logging_enabled": True,
                }
            ],
            access_log_destination_arn="arn:aws:logs:us-east-1:123:log-group:/test",
            access_log_format=custom_format,
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert custom_format in hcl

    def test_default_route_settings_emitted_with_stage(self):
        """default_route_settings block emitted when throttling/metrics fields set."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            stages=[{"name": "$default", "auto_deploy": True}],
            default_route_throttling_burst_limit=100,
            default_route_throttling_rate_limit=50.0,
            default_route_detailed_metrics_enabled=True,
            default_route_logging_level="INFO",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "default_route_settings" in hcl
        assert "throttling_burst_limit" in hcl
        assert "throttling_rate_limit" in hcl
        assert "detailed_metrics_enabled" in hcl
        assert "logging_level" in hcl

    def test_data_trace_enabled_in_default_route_settings(self):
        """data_trace_enabled is emitted in default_route_settings."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            stages=[{"name": "$default", "auto_deploy": True}],
            default_route_data_trace_enabled=True,
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "default_route_settings" in hcl
        assert "data_trace_enabled" in hcl

    def test_variables_tf_emits_access_log_variables(self):
        """generate_variables_tf emits variable blocks for stage fields."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            access_log_destination_arn="arn:aws:logs:us-east-1:123:log-group:/test",
            default_route_throttling_burst_limit=100,
        )
        instance = _make_instance("test_api", config)
        vars_tf = self.gen.generate_variables_tf(instance)

        assert "access_log_destination_arn" in vars_tf
        assert "default_route_throttling_burst_limit" in vars_tf


# ===========================================================================
# Test authorizer TTL and simple_responses attributes (Requirement 4.10)
# ===========================================================================


class TestAuthorizerTTLAndSimpleResponses:
    """Authorizer fields produce TTL and simple_responses in aws_apigatewayv2_authorizer."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_authorizer_ttl_emitted(self):
        """authorizer_result_ttl_in_seconds is emitted in authorizer resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "my_auth",
                    "type": "JWT",
                    "issuer": "https://example.com",
                    "audience": ["aud1"],
                }
            ],
            authorizer_result_ttl_in_seconds=300,
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_authorizer"' in hcl
        assert "authorizer_result_ttl_in_seconds" in hcl
        assert "300" in hcl

    def test_enable_simple_responses_emitted(self):
        """enable_simple_responses is emitted in authorizer resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "my_auth",
                    "type": "JWT",
                    "issuer": "https://example.com",
                    "audience": ["aud1"],
                }
            ],
            enable_simple_responses=True,
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_authorizer"' in hcl
        assert "enable_simple_responses" in hcl
        assert "true" in hcl

    def test_authorizer_credentials_arn_emitted(self):
        """authorizer_credentials_arn is emitted when set."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "my_auth",
                    "type": "JWT",
                    "issuer": "https://example.com",
                    "audience": ["aud1"],
                }
            ],
            authorizer_credentials_arn="arn:aws:iam::123:role/auth-role",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "authorizer_credentials_arn" in hcl
        assert "var.authorizer_credentials_arn" in hcl

    def test_identity_sources_emitted(self):
        """identity_sources is emitted in authorizer resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "my_auth",
                    "type": "JWT",
                    "issuer": "https://example.com",
                    "audience": ["aud1"],
                }
            ],
            identity_sources=["$request.header.Authorization"],
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "identity_sources" in hcl
        assert "$request.header.Authorization" in hcl

    def test_variables_tf_emits_authorizer_variables(self):
        """generate_variables_tf emits variable blocks for authorizer fields."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorizer_result_ttl_in_seconds=300,
            enable_simple_responses=True,
            authorizer_credentials_arn="arn:aws:iam::123:role/auth-role",
            identity_sources=["$request.header.Authorization"],
        )
        instance = _make_instance("test_api", config)
        vars_tf = self.gen.generate_variables_tf(instance)

        assert "authorizer_result_ttl_in_seconds" in vars_tf
        assert "enable_simple_responses" in vars_tf
        assert "authorizer_credentials_arn" in vars_tf
        assert "identity_sources" in vars_tf


# ===========================================================================
# Test integration timeout and connection fields emission (Requirement 4.11)
# ===========================================================================


class TestIntegrationTimeoutAndConnectionFields:
    """Integration fields produce timeout and connection attrs in aws_apigatewayv2_integration."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_timeout_milliseconds_emitted(self):
        """timeout_milliseconds is emitted in integration resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            integrations=[
                {
                    "name": "backend",
                    "type": "HTTP_PROXY",
                    "uri": "https://backend.com",
                    "method": "ANY",
                }
            ],
            timeout_milliseconds=5000,
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_integration"' in hcl
        assert "timeout_milliseconds" in hcl
        assert "5000" in hcl

    def test_tls_server_name_to_verify_emitted_as_tls_config(self):
        """tls_server_name_to_verify is emitted inside a tls_config block."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            integrations=[
                {
                    "name": "backend",
                    "type": "HTTP_PROXY",
                    "uri": "https://backend.com",
                    "method": "ANY",
                }
            ],
            tls_server_name_to_verify="backend.com",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "tls_config" in hcl
        assert "server_name_to_verify" in hcl
        assert "backend.com" in hcl

    def test_connection_type_and_id_emitted(self):
        """connection_type and connection_id are emitted in integration resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            integrations=[
                {
                    "name": "backend",
                    "type": "HTTP_PROXY",
                    "uri": "https://backend.com",
                    "method": "ANY",
                }
            ],
            connection_type="VPC_LINK",
            connection_id="vpc-link-123",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "connection_type" in hcl
        assert "VPC_LINK" in hcl
        assert "connection_id" in hcl
        assert "vpc-link-123" in hcl

    def test_content_handling_strategy_emitted(self):
        """content_handling_strategy is emitted in integration resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            integrations=[
                {
                    "name": "backend",
                    "type": "HTTP_PROXY",
                    "uri": "https://backend.com",
                    "method": "ANY",
                }
            ],
            content_handling_strategy="CONVERT_TO_TEXT",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "content_handling_strategy" in hcl
        assert "CONVERT_TO_TEXT" in hcl

    def test_integration_subtype_emitted(self):
        """integration_subtype is emitted in integration resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            integrations=[
                {
                    "name": "backend",
                    "type": "HTTP_PROXY",
                    "uri": "https://backend.com",
                    "method": "ANY",
                }
            ],
            integration_subtype="EventBridge-PutEvents",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "integration_subtype" in hcl
        assert "EventBridge-PutEvents" in hcl

    def test_variables_tf_emits_integration_variables(self):
        """generate_variables_tf emits variable blocks for integration fields."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            timeout_milliseconds=5000,
            tls_server_name_to_verify="backend.com",
            connection_type="VPC_LINK",
            connection_id="vpc-link-123",
        )
        instance = _make_instance("test_api", config)
        vars_tf = self.gen.generate_variables_tf(instance)

        assert "timeout_milliseconds" in vars_tf
        assert "tls_server_name_to_verify" in vars_tf
        assert "connection_type" in vars_tf
        assert "connection_id" in vars_tf


# ===========================================================================
# Test domain mTLS attributes emission (Requirement 4.12)
# ===========================================================================


class TestDomainMTLSAttributes:
    """Domain fields produce mutual_tls_authentication in aws_apigatewayv2_domain_name."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_mutual_tls_truststore_uri_emits_mtls_block(self):
        """mutual_tls_truststore_uri produces mutual_tls_authentication block."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            custom_domain={
                "domain_name": "api.example.com",
                "certificate_arn": "arn:aws:acm:us-east-1:123:certificate/abc",
            },
            mutual_tls_truststore_uri="s3://bucket/truststore.pem",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_domain_name"' in hcl
        assert "mutual_tls_authentication" in hcl
        assert "truststore_uri" in hcl
        assert "s3://bucket/truststore.pem" in hcl

    def test_mutual_tls_truststore_version_emitted(self):
        """mutual_tls_truststore_version is included in mutual_tls_authentication block."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            custom_domain={
                "domain_name": "api.example.com",
                "certificate_arn": "arn:aws:acm:us-east-1:123:certificate/abc",
            },
            mutual_tls_truststore_uri="s3://bucket/truststore.pem",
            mutual_tls_truststore_version="v1",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "truststore_version" in hcl
        assert "v1" in hcl

    def test_endpoint_type_and_security_policy_in_domain(self):
        """endpoint_type and security_policy are emitted in domain_name_configuration."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            custom_domain={
                "domain_name": "api.example.com",
                "certificate_arn": "arn:aws:acm:us-east-1:123:certificate/abc",
            },
            endpoint_type="REGIONAL",
            security_policy="TLS_1_2",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "endpoint_type" in hcl
        assert "REGIONAL" in hcl
        assert "security_policy" in hcl
        assert "TLS_1_2" in hcl

    def test_no_mtls_block_without_truststore_uri(self):
        """No mutual_tls_authentication block when truststore URI is not set."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            custom_domain={
                "domain_name": "api.example.com",
                "certificate_arn": "arn:aws:acm:us-east-1:123:certificate/abc",
            },
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_domain_name"' in hcl
        assert "mutual_tls_authentication" not in hcl

    def test_variables_tf_emits_domain_variables(self):
        """generate_variables_tf emits variable blocks for domain fields."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            mutual_tls_truststore_uri="s3://bucket/truststore.pem",
            mutual_tls_truststore_version="v1",
            endpoint_type="REGIONAL",
            security_policy="TLS_1_2",
        )
        instance = _make_instance("test_api", config)
        vars_tf = self.gen.generate_variables_tf(instance)

        assert "mutual_tls_truststore_uri" in vars_tf
        assert "mutual_tls_truststore_version" in vars_tf
        assert "endpoint_type" in vars_tf
        assert "security_policy" in vars_tf


# ===========================================================================
# Test route authorization_type and scopes emission (Requirement 4.13)
# ===========================================================================


class TestRouteAuthorizationTypeAndScopes:
    """Route fields produce authorization_type and scopes in aws_apigatewayv2_route."""

    def setup_method(self):
        self.gen = APIGatewayGenerator()

    def test_authorization_type_emitted_on_default_route(self):
        """authorization_type is emitted on the $default route when set at config level."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorization_type="JWT",
            api_key_required=True,  # triggers route generation
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert 'resource "aws_apigatewayv2_route"' in hcl
        assert "authorization_type" in hcl
        assert "JWT" in hcl

    def test_authorization_scopes_emitted_on_route(self):
        """authorization_scopes are emitted on the route resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorization_type="JWT",
            authorization_scopes=["read", "write"],
            api_key_required=True,  # triggers route generation
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "authorization_scopes" in hcl
        assert "read" in hcl
        assert "write" in hcl

    def test_operation_name_emitted_on_route(self):
        """operation_name is emitted on the route resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            operation_name="GetUsers",
            api_key_required=True,  # triggers route generation
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "operation_name" in hcl
        assert "GetUsers" in hcl

    def test_route_response_selection_expression_emitted(self):
        """route_response_selection_expression is emitted on the route resource."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            route_response_selection_expression="$default",
            api_key_required=True,  # triggers route generation
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "route_response_selection_expression" in hcl

    def test_per_route_authorization_type_overrides_config(self):
        """Per-route authorization_type takes precedence over config-level value."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {
                    "method": "GET",
                    "path": "/users",
                    "authorization_type": "AWS_IAM",
                }
            ],
            authorization_type="JWT",
        )
        instance = _make_instance("test_api", config)
        hcl = self.gen.generate_resource_tf(instance)

        assert "authorization_type" in hcl
        assert "AWS_IAM" in hcl

    def test_variables_tf_emits_route_variables(self):
        """generate_variables_tf emits variable blocks for route fields."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            authorization_type="JWT",
            authorization_scopes=["read", "write"],
            operation_name="GetUsers",
            route_response_selection_expression="$default",
        )
        instance = _make_instance("test_api", config)
        vars_tf = self.gen.generate_variables_tf(instance)

        assert "authorization_type" in vars_tf
        assert "authorization_scopes" in vars_tf
        assert "operation_name" in vars_tf
        assert "route_response_selection_expression" in vars_tf
