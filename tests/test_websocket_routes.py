"""WebSocket APIs address routes by key, not by path."""

import pytest

from app.generators.api_gateway import routes
from app.generators.api_gateway._support import resolve_config
from app.generators.api_gateway_generator import APIGatewayGenerator
from app.generators.api_gateway_validator import APIGatewayValidator
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ServiceType
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def _instance(config: ApiGatewayConfig) -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name="ws-api", service_type=ServiceType.API_GATEWAY, config=config
    )


def _websocket(route_keys: list[str]) -> ResourceInstanceIR:
    return _instance(
        ApiGatewayConfig(
            api_name="ws-api",
            protocol_type="WEBSOCKET",
            route_selection_expression="$request.body.action",
            routes=[
                {"methods": ["ANY"], "path": key, "integration_name": "fn"}
                for key in route_keys
            ],
        )
    )


class TestWebSocketRouteKeys:
    @pytest.mark.parametrize("key", ["$connect", "$disconnect", "$default"])
    def test_special_route_keys_are_accepted(self, key):
        assert APIGatewayValidator().validate(_websocket([key])) == []

    def test_custom_route_keys_are_accepted(self):
        assert APIGatewayValidator().validate(_websocket(["sendMessage"])) == []

    def test_route_keys_reach_the_generated_hcl(self):
        instance = _websocket(["$connect", "$disconnect", "sendMessage"])
        hcl = routes.render_routes(instance, resolve_config(instance), HCLRenderer())
        for key in ("$connect", "$disconnect", "sendMessage"):
            assert f'route_key = "{key}"' in hcl

    def test_a_whole_websocket_api_generates(self):
        instance = _websocket(["$connect", "$default"])
        assert "protocol_type = var.protocol_type" in (
            APIGatewayGenerator().generate_resource_tf(instance)
        )


class TestHttpPathsAreStillChecked:
    def test_http_rejects_a_websocket_style_key(self):
        instance = _instance(
            ApiGatewayConfig(
                api_name="http-api",
                protocol_type="HTTP",
                routes=[{"methods": ["GET"], "path": "$connect"}],
            )
        )
        codes = [e.code for e in APIGatewayValidator().validate(instance)]
        assert "INVALID_PATH" in codes

    def test_http_allows_the_default_route_key(self):
        instance = _instance(
            ApiGatewayConfig(
                api_name="http-api",
                protocol_type="HTTP",
                routes=[{"methods": ["ANY"], "path": "$default"}],
            )
        )
        assert APIGatewayValidator().validate(instance) == []

    def test_http_still_rejects_a_malformed_path(self):
        instance = _instance(
            ApiGatewayConfig(
                api_name="http-api",
                protocol_type="HTTP",
                routes=[{"methods": ["GET"], "path": "no-leading-slash"}],
            )
        )
        codes = [e.code for e in APIGatewayValidator().validate(instance)]
        assert "INVALID_PATH" in codes


class TestUnnamedIntegration:
    def _with_integrations(self, integrations: list[dict]) -> ResourceInstanceIR:
        return _instance(
            ApiGatewayConfig(
                api_name="api",
                protocol_type="HTTP",
                routes=[{"methods": ["GET"], "path": "/x"}],
                integrations=integrations,
            )
        )

    def test_missing_name_is_reported(self):
        instance = self._with_integrations([{"type": "HTTP_PROXY", "uri": "https://b"}])
        codes = [e.code for e in APIGatewayValidator().validate(instance)]
        assert "MISSING_INTEGRATION_NAME" in codes

    def test_generator_does_not_crash_on_it(self):
        instance = self._with_integrations([{"type": "HTTP_PROXY", "uri": "https://b"}])
        # The validator rejects this, but the generator must not raise KeyError
        routes.render_routes(instance, resolve_config(instance), HCLRenderer())

    def test_named_integration_passes(self):
        instance = self._with_integrations(
            [{"name": "fn", "type": "HTTP_PROXY", "uri": "https://b"}]
        )
        codes = [e.code for e in APIGatewayValidator().validate(instance)]
        assert "MISSING_INTEGRATION_NAME" not in codes
