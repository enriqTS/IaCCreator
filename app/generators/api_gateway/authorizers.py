"""JWT and Lambda authorizers."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_authorizers(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_authorizer resources for each configured authorizer.

    Supports three authorizer types:
    - JWT: authorizer_type = "JWT" with jwt_configuration block (issuer + audience)
    - REQUEST (Lambda): authorizer_type = "REQUEST" with authorizer_uri and payload_format_version
    - COGNITO_USER_POOLS: authorizer_type = "JWT" with jwt_configuration using
      cognito_user_pool_endpoint as issuer and cognito_client_ids as audience

    Also includes optional fields from TerraformField config:
    - authorizer_result_ttl_in_seconds
    - enable_simple_responses
    - authorizer_credentials_arn
    - identity_sources
    """
    authorizers = getattr(config, "authorizers", None)
    if not authorizers:
        return ""

    parts: list[str] = []

    for authorizer in authorizers:
        auth_name = authorizer["name"]
        auth_type = authorizer.get("type", "JWT")
        resource_name = f"{instance.name}_{auth_name}_authorizer"

        attrs: dict = {
            "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
            "name": auth_name,
        }

        if auth_type == "JWT":
            attrs["authorizer_type"] = "JWT"
            jwt_config: dict = {}
            if authorizer.get("issuer"):
                jwt_config["issuer"] = authorizer["issuer"]
            if authorizer.get("audience"):
                jwt_config["audience"] = authorizer["audience"]
            if jwt_config:
                attrs["jwt_configuration"] = jwt_config

        elif auth_type == "REQUEST":
            attrs["authorizer_type"] = "REQUEST"
            if authorizer.get("lambda_arn"):
                attrs["authorizer_uri"] = authorizer["lambda_arn"]
            payload_version = authorizer.get("payload_format_version", "2.0")
            attrs["authorizer_payload_format_version"] = payload_version

        elif auth_type == "COGNITO_USER_POOLS":
            attrs["authorizer_type"] = "JWT"
            jwt_config = {}
            if authorizer.get("cognito_user_pool_endpoint"):
                jwt_config["issuer"] = authorizer["cognito_user_pool_endpoint"]
            if authorizer.get("cognito_client_ids"):
                jwt_config["audience"] = authorizer["cognito_client_ids"]
            if jwt_config:
                attrs["jwt_configuration"] = jwt_config

        # New optional authorizer fields from TerraformField config
        # Use per-authorizer dict values first, then fall back to top-level config fields
        result_ttl = authorizer.get("authorizer_result_ttl_in_seconds")
        if result_ttl is None:
            result_ttl = getattr(config, "authorizer_result_ttl_in_seconds", None)
        if result_ttl is not None:
            attrs["authorizer_result_ttl_in_seconds"] = result_ttl

        enable_simple = authorizer.get("enable_simple_responses")
        if enable_simple is None:
            enable_simple = getattr(config, "enable_simple_responses", None)
        if enable_simple is not None:
            attrs["enable_simple_responses"] = enable_simple

        creds_arn = authorizer.get("authorizer_credentials_arn")
        if creds_arn is None:
            creds_arn = getattr(config, "authorizer_credentials_arn", None)
        if creds_arn is not None:
            attrs["authorizer_credentials_arn"] = Expr("var.authorizer_credentials_arn")

        identity_src = authorizer.get("identity_sources")
        if identity_src is None:
            identity_src = getattr(config, "identity_sources", None)
        if identity_src is not None:
            attrs["identity_sources"] = identity_src

        parts.append(
            r.render_resource("aws_apigatewayv2_authorizer", resource_name, attrs)
        )

    return "\n".join(parts)


def render_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Variable blocks this concern contributes."""
    parts: list[str] = []
    # ─── Authorizers fields ───────────────────────────────────────────────
    if config.authorizer_result_ttl_in_seconds is not None:
        parts.append(
            r.render_variable(
                "authorizer_result_ttl_in_seconds",
                "number",
                "Time to live (TTL) for cached authorizer results in seconds",
                default=config.authorizer_result_ttl_in_seconds,
            )
        )
    if config.enable_simple_responses is not None:
        parts.append(
            r.render_variable(
                "enable_simple_responses",
                "bool",
                "Whether to enable simple responses for the authorizer",
                default=config.enable_simple_responses,
            )
        )
    if config.authorizer_credentials_arn is not None:
        parts.append(
            r.render_variable(
                "authorizer_credentials_arn",
                "string",
                "Credentials ARN for the authorizer",
                default=config.authorizer_credentials_arn,
            )
        )
    if config.identity_sources is not None:
        parts.append(
            r.render_variable(
                "identity_sources",
                "list(string)",
                "Identity sources for the authorizer",
                default=config.identity_sources,
            )
        )
    return parts
