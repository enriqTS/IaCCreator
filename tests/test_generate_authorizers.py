"""Unit tests for APIGatewayGenerator._generate_authorizers method."""


from app.generators.api_gateway_generator import APIGatewayGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_instance(name: str, config: ResourceConfig) -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.API_GATEWAY,
        config=config,
    )


class TestGenerateAuthorizersEmpty:
    """Tests for when no authorizers are configured."""

    def test_no_authorizers_returns_empty_string(self):
        config = ResourceConfig(protocol_type="HTTP")
        instance = _make_instance("my_api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)
        assert result == ""

    def test_empty_authorizers_list_returns_empty_string(self):
        config = ResourceConfig(protocol_type="HTTP", authorizers=[])
        instance = _make_instance("my_api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)
        assert result == ""


class TestGenerateAuthorizersJWT:
    """Tests for JWT authorizer generation."""

    def test_jwt_authorizer_basic(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "my_jwt",
                    "type": "JWT",
                    "issuer": "https://auth.example.com/",
                    "audience": ["api-client-1"],
                }
            ],
        )
        instance = _make_instance("my_api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        assert (
            'resource "aws_apigatewayv2_authorizer" "my_api_my_jwt_authorizer"'
            in result
        )
        assert 'authorizer_type = "JWT"' in result
        assert "jwt_configuration {" in result
        assert 'issuer = "https://auth.example.com/"' in result
        assert 'audience = ["api-client-1"]' in result
        assert "api_id" in result
        assert 'name = "my_jwt"' in result

    def test_jwt_authorizer_multiple_audiences(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "multi_aud",
                    "type": "JWT",
                    "issuer": "https://issuer.example.com",
                    "audience": ["client-a", "client-b", "client-c"],
                }
            ],
        )
        instance = _make_instance("api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        assert 'audience = ["client-a", "client-b", "client-c"]' in result


class TestGenerateAuthorizersLambda:
    """Tests for Lambda (REQUEST) authorizer generation."""

    def test_lambda_authorizer_basic(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "lambda_auth",
                    "type": "REQUEST",
                    "lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:my-authorizer",
                    "payload_format_version": "2.0",
                }
            ],
        )
        instance = _make_instance("my_api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        assert (
            'resource "aws_apigatewayv2_authorizer" "my_api_lambda_auth_authorizer"'
            in result
        )
        assert 'authorizer_type = "REQUEST"' in result
        assert (
            'authorizer_uri = "arn:aws:lambda:us-east-1:123456789012:function:my-authorizer"'
            in result
        )
        assert 'authorizer_payload_format_version = "2.0"' in result
        assert 'name = "lambda_auth"' in result

    def test_lambda_authorizer_payload_version_1_0(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "lambda_v1",
                    "type": "REQUEST",
                    "lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:auth",
                    "payload_format_version": "1.0",
                }
            ],
        )
        instance = _make_instance("api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        assert 'authorizer_payload_format_version = "1.0"' in result

    def test_lambda_authorizer_default_payload_version(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "lambda_default",
                    "type": "REQUEST",
                    "lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:auth",
                }
            ],
        )
        instance = _make_instance("api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        # Default payload_format_version should be "2.0"
        assert 'authorizer_payload_format_version = "2.0"' in result


class TestGenerateAuthorizersCognito:
    """Tests for Cognito User Pools authorizer generation."""

    def test_cognito_authorizer_basic(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "cognito_auth",
                    "type": "COGNITO_USER_POOLS",
                    "cognito_user_pool_endpoint": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123",
                    "cognito_client_ids": ["client-id-1", "client-id-2"],
                }
            ],
        )
        instance = _make_instance("my_api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        assert (
            'resource "aws_apigatewayv2_authorizer" "my_api_cognito_auth_authorizer"'
            in result
        )
        # Cognito uses JWT type in API Gateway v2
        assert 'authorizer_type = "JWT"' in result
        assert "jwt_configuration {" in result
        assert (
            'issuer = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123"'
            in result
        )
        assert 'audience = ["client-id-1", "client-id-2"]' in result
        assert 'name = "cognito_auth"' in result


class TestGenerateAuthorizersMultiple:
    """Tests for multiple authorizers in a single API."""

    def test_multiple_authorizers_different_types(self):
        config = ResourceConfig(
            protocol_type="HTTP",
            authorizers=[
                {
                    "name": "jwt_auth",
                    "type": "JWT",
                    "issuer": "https://auth.example.com/",
                    "audience": ["client-1"],
                },
                {
                    "name": "lambda_auth",
                    "type": "REQUEST",
                    "lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:auth",
                    "payload_format_version": "2.0",
                },
                {
                    "name": "cognito_auth",
                    "type": "COGNITO_USER_POOLS",
                    "cognito_user_pool_endpoint": "https://cognito-idp.us-east-1.amazonaws.com/pool",
                    "cognito_client_ids": ["cid-1"],
                },
            ],
        )
        instance = _make_instance("my_api", config)
        gen = APIGatewayGenerator()
        result = gen._generate_authorizers(instance)

        # All three authorizer resources should be present
        assert '"my_api_jwt_auth_authorizer"' in result
        assert '"my_api_lambda_auth_authorizer"' in result
        assert '"my_api_cognito_auth_authorizer"' in result

        # Count resource blocks
        assert result.count('resource "aws_apigatewayv2_authorizer"') == 3
