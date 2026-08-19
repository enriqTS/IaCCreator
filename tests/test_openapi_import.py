"""OpenAPI import: parsing and mapping onto API Gateway configuration."""

import pytest

from app.services.openapi.mapper import map_openapi
from app.services.openapi.parser import OpenApiParseError, parse_openapi

MINIMAL = """
openapi: 3.0.0
info:
  title: Petstore
  description: A demo API
servers:
  - url: https://api.example.com
paths:
  /pets:
    get:
      tags: [pets]
      responses: {}
    post:
      responses: {}
"""


def _map(text: str, server: str | None = None):
    return map_openapi(parse_openapi(text), server)


class TestParsing:
    def test_accepts_json(self):
        document = parse_openapi('{"openapi":"3.0.0","info":{},"paths":{}}')
        assert document.openapi == "3.0.0"

    def test_accepts_yaml(self):
        assert parse_openapi(MINIMAL).info["title"] == "Petstore"

    def test_rejects_garbage(self):
        with pytest.raises(OpenApiParseError, match="not valid JSON or YAML"):
            parse_openapi("\t: [unbalanced")

    def test_rejects_swagger_2(self):
        with pytest.raises(OpenApiParseError, match="openapi"):
            parse_openapi('{"swagger":"2.0","info":{},"paths":{}}')

    def test_rejects_missing_paths(self):
        with pytest.raises(OpenApiParseError, match="paths"):
            parse_openapi('{"openapi":"3.0.0","info":{}}')


class TestRouteMapping:
    def test_one_route_per_method(self):
        result = _map(MINIMAL)
        assert {(tuple(r.methods), r.path) for r in result.routes} == {
            (("GET",), "/pets"),
            (("POST",), "/pets"),
        }

    def test_tag_is_carried_through(self):
        route = next(r for r in _map(MINIMAL).routes if r.methods == ["GET"])
        assert route.tag == "pets"

    def test_target_uri_uses_the_selected_server(self):
        route = _map(MINIMAL, "https://api.example.com").routes[0]
        assert route.target_service_uri == "https://api.example.com/pets"

    def test_target_uri_absent_without_a_server_choice(self):
        assert _map(MINIMAL).routes[0].target_service_uri is None


SECURED = """
openapi: 3.0.0
info: {title: Secured}
security:
  - ApiKeyAuth: []
components:
  securitySchemes:
    ApiKeyAuth: {type: apiKey, in: header, name: X-API-Key}
    OidcAuth: {type: openIdConnect, openIdConnectUrl: https://issuer/config}
    OAuth:
      type: oauth2
      flows:
        clientCredentials: {tokenUrl: https://issuer/token}
paths:
  /open:
    get:
      security: []
      responses: {}
  /jwt:
    get:
      security: [{OidcAuth: []}]
      responses: {}
  /inherited:
    get:
      responses: {}
"""


class TestSecurityMapping:
    def test_global_api_key_is_detected(self):
        assert _map(SECURED).settings.api_key_required is True

    def test_operation_security_overrides_global(self):
        route = next(r for r in _map(SECURED).routes if r.path == "/open")
        assert route.api_key_required is False
        assert route.authorizer_name is None

    def test_jwt_scheme_becomes_an_authorizer_reference(self):
        route = next(r for r in _map(SECURED).routes if r.path == "/jwt")
        assert route.authorizer_name == "OidcAuth"

    def test_global_security_applies_when_operation_is_silent(self):
        route = next(r for r in _map(SECURED).routes if r.path == "/inherited")
        assert route.api_key_required is True

    def test_authorizers_come_from_jwt_schemes_only(self):
        authorizers = {a.name: a.issuer_url for a in _map(SECURED).authorizers}
        assert authorizers == {
            "OidcAuth": "https://issuer/config",
            "OAuth": "https://issuer/token",
        }


CORS = """
openapi: 3.0.0
info: {title: Cors}
paths:
  /things:
    options:
      responses:
        "204":
          headers:
            Access-Control-Allow-Origin:
              schema: {default: "*"}
            Access-Control-Allow-Methods:
              schema: {default: "GET,POST"}
"""


class TestCorsDetection:
    def test_cors_headers_are_collected(self):
        settings = _map(CORS).settings
        assert settings.cors_configuration == {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST",
        }

    def test_summary_reports_cors(self):
        assert _map(CORS).summary.has_cors is True

    def test_absent_cors_is_reported(self):
        assert _map(MINIMAL).summary.has_cors is False


class TestSummary:
    def test_counts_match_the_content(self):
        summary = _map(SECURED).summary
        assert summary.route_count == 3
        assert summary.authorizer_count == 2
        assert summary.has_api_key is True
