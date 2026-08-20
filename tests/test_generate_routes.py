"""Unit tests for the routes sub-generator."""

from app.generators.api_gateway import routes
from app.generators.api_gateway._support import resolve_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ServiceType
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def _make_instance(name: str, config: ApiGatewayConfig) -> ResourceInstanceIR:
    """Create a ResourceInstanceIR for testing."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.API_GATEWAY,
        config=config,
    )


class TestGenerateRoutesHTTP:
    """Tests for HTTP API route generation."""

    def test_default_route_when_no_routes_configured(self):
        """When no routes configured for HTTP API, generates $default route."""
        instance = _make_instance(
            "my_api", ApiGatewayConfig(api_name="test-api", protocol_type="HTTP")
        )
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'resource "aws_apigatewayv2_route" "my_api_default_route"' in hcl
        assert 'route_key = "$default"' in hcl
        assert "aws_apigatewayv2_api.my_api.id" in hcl

    def test_generates_route_for_each_configured_entry(self):
        """Generates a route resource for each configured route."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {"methods": ["GET"], "path": "/users"},
                {"methods": ["POST"], "path": "/users"},
            ],
        )
        instance = _make_instance("my_api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'route_key = "GET /users"' in hcl
        assert 'route_key = "POST /users"' in hcl
        # 2 resource blocks, each with one "aws_apigatewayv2_route" in the resource line
        assert hcl.count('resource "aws_apigatewayv2_route"') == 2

    def test_route_key_format(self):
        """Route key is formatted as '{METHOD} {path}'."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[{"methods": ["DELETE"], "path": "/items/{id}"}],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'route_key = "DELETE /items/{id}"' in hcl

    def test_authorization_on_http_route(self):
        """Routes referencing authorizers get authorization_type and authorizer_id."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {"methods": ["GET"], "path": "/secure", "authorizer_name": "jwt_auth"}
            ],
            authorizers=[
                {
                    "name": "jwt_auth",
                    "type": "JWT",
                    "issuer": "https://example.com",
                    "audience": ["api"],
                }
            ],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'authorization_type = "JWT"' in hcl
        assert "aws_apigatewayv2_authorizer.api_jwt_auth_authorizer.id" in hcl

    def test_lambda_authorizer_sets_custom_type(self):
        """Lambda (REQUEST) authorizer sets authorization_type = CUSTOM."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {
                    "methods": ["GET"],
                    "path": "/protected",
                    "authorizer_name": "lambda_auth",
                }
            ],
            authorizers=[
                {
                    "name": "lambda_auth",
                    "type": "REQUEST",
                    "lambda_arn": "arn:aws:lambda:us-east-1:123:function:auth",
                }
            ],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'authorization_type = "CUSTOM"' in hcl
        assert "aws_apigatewayv2_authorizer.api_lambda_auth_authorizer.id" in hcl

    def test_api_key_required_on_routes(self):
        """When api_key_required is True, all routes get api_key_required = true."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[{"methods": ["GET"], "path": "/data"}],
            api_key_required=True,
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert "api_key_required = true" in hcl

    def test_api_key_required_on_default_route(self):
        """When api_key_required is True and no routes, $default route gets api_key_required."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            api_key_required=True,
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'route_key = "$default"' in hcl
        assert "api_key_required = true" in hcl

    def test_integration_target_on_route(self):
        """Routes with integration_name get a target attribute."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {
                    "methods": ["GET"],
                    "path": "/users",
                    "integration_name": "lambda_backend",
                }
            ],
            integrations=[{"name": "lambda_backend", "type": "AWS_PROXY"}],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert "target" in hcl
        assert "aws_apigatewayv2_integration.api_lambda_backend_integration.id" in hcl

    def test_undefined_authorizer_not_added(self):
        """Routes referencing undefined authorizers don't get authorization attributes."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {"methods": ["GET"], "path": "/data", "authorizer_name": "nonexistent"}
            ],
            authorizers=[],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert "authorization_type" not in hcl
        assert "authorizer_id" not in hcl

    def test_skips_connection_derived_routes(self):
        """Routes with connection-derived integration_name (not in config.integrations) are skipped.

        These routes are handled by ApiGatewayLambdaHandler which generates both
        the route and its integration target properly.
        """
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {
                    "methods": ["GET"],
                    "path": "/users",
                    "integration_name": "lambda_backend",
                },
                {
                    "methods": ["POST"],
                    "path": "/users",
                    "integration_name": "lambda_backend",
                },
            ],
            # No config.integrations - routes reference lambda by name only (connection-derived)
            integrations=[],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        # Routes should be skipped entirely (not emitted at all)
        assert "GET /users" not in hcl
        assert "POST /users" not in hcl
        assert (
            hcl.strip() == "" or "$default" in hcl
        )  # Should fall back to default route

    def test_emits_routes_with_matching_manual_integrations(self):
        """Routes with integration_name found in config.integrations are emitted."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="HTTP",
            routes=[
                {
                    "methods": ["GET"],
                    "path": "/users",
                    "integration_name": "manual_integration",
                },
            ],
            integrations=[{"name": "manual_integration", "type": "HTTP_PROXY"}],
        )
        instance = _make_instance("api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        # Route with matching manual integration should be emitted
        assert 'route_key = "GET /users"' in hcl
        assert "target" in hcl
        assert (
            "aws_apigatewayv2_integration.api_manual_integration_integration.id" in hcl
        )


class TestGenerateRoutesWebSocket:
    """Tests for WebSocket API route generation."""

    def test_generates_special_routes(self):
        """WebSocket APIs always generate $connect, $disconnect, $default routes."""
        config = ApiGatewayConfig(api_name="test-api", protocol_type="WEBSOCKET")
        instance = _make_instance("ws_api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'route_key = "$connect"' in hcl
        assert 'route_key = "$disconnect"' in hcl
        assert 'route_key = "$default"' in hcl

    def test_custom_routes_added(self):
        """Custom WebSocket routes are generated alongside special routes."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="WEBSOCKET",
            routes=[{"path": "sendMessage"}],
        )
        instance = _make_instance("ws_api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        assert 'route_key = "$connect"' in hcl
        assert 'route_key = "$disconnect"' in hcl
        assert 'route_key = "$default"' in hcl
        assert 'route_key = "sendMessage"' in hcl

    def test_only_connect_gets_authorization(self):
        """Only $connect route gets authorization attributes (Property 4)."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="WEBSOCKET",
            routes=[
                {"path": "$connect", "authorizer_name": "jwt_auth"},
                {"path": "$disconnect", "authorizer_name": "jwt_auth"},
                {"path": "$default", "authorizer_name": "jwt_auth"},
            ],
            authorizers=[
                {
                    "name": "jwt_auth",
                    "type": "JWT",
                    "issuer": "https://example.com",
                    "audience": ["api"],
                }
            ],
        )
        instance = _make_instance("ws_api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        # Split into individual route blocks to check each one
        blocks = hcl.split('resource "aws_apigatewayv2_route"')
        connect_block = next(
            b for b in blocks if "connect_route" in b and "disconnect" not in b
        )
        disconnect_block = next(b for b in blocks if "disconnect_route" in b)
        default_block = next(b for b in blocks if "default_route" in b)

        # $connect should have authorization
        assert "authorization_type" in connect_block
        assert "authorizer_id" in connect_block

        # $disconnect and $default should NOT have authorization
        assert "authorization_type" not in disconnect_block
        assert "authorizer_id" not in disconnect_block
        assert "authorization_type" not in default_block
        assert "authorizer_id" not in default_block

    def test_api_key_required_on_websocket_routes(self):
        """When api_key_required is True, all WebSocket routes get api_key_required."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="WEBSOCKET",
            api_key_required=True,
        )
        instance = _make_instance("ws_api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        # All 3 special routes should have api_key_required
        assert hcl.count("api_key_required = true") == 3

    def test_duplicate_special_routes_not_generated(self):
        """If routes config includes $connect, it's not duplicated."""
        config = ApiGatewayConfig(
            api_name="test-api",
            protocol_type="WEBSOCKET",
            routes=[
                {"path": "$connect", "integration_name": "auth_fn"},
                {"path": "chat"},
            ],
            integrations=[{"name": "auth_fn", "type": "AWS_PROXY"}],
        )
        instance = _make_instance("ws_api", config)
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())

        # $connect should appear exactly once as a route_key
        assert hcl.count('route_key = "$connect"') == 1
        # Custom route should also appear
        assert 'route_key = "chat"' in hcl
