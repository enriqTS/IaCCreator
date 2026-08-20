"""The API resource itself, and the settings that belong to it."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_api_resource(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_api resource block."""
    attrs: dict = {
        "name": Expr("var.api_name"),
        "protocol_type": Expr("var.protocol_type"),
    }
    if config.description is not None:
        attrs["description"] = Expr("var.description")
    if config.cors_configuration is not None:
        attrs["cors_configuration"] = Expr("var.cors_configuration")
    if config.disable_execute_api_endpoint is not None:
        attrs["disable_execute_api_endpoint"] = Expr("var.disable_execute_api_endpoint")
    # route_selection_expression — only when protocol_type is WEBSOCKET (visible_when)
    if config.protocol_type == "WEBSOCKET":
        if config.route_selection_expression is not None:
            attrs["route_selection_expression"] = Expr("var.route_selection_expression")
    if config.tags is not None:
        attrs["tags"] = Expr("var.tags")

    # API key selection expression when api_key_required is true
    if config.api_key_required:
        attrs["api_key_selection_expression"] = "$request.header.x-api-key"

    # API key selection expression for WEBSOCKET with api_keys list
    api_keys = getattr(config, "api_keys", None)
    if api_keys and config.protocol_type == "WEBSOCKET" and not config.api_key_required:
        attrs["api_key_selection_expression"] = "$request.header.x-api-key"

    # New General-level optional fields
    if config.api_key_selection_expression is not None and not config.api_key_required:
        attrs["api_key_selection_expression"] = Expr("var.api_key_selection_expression")
    if config.ip_address_type is not None:
        attrs["ip_address_type"] = Expr("var.ip_address_type")
    if config.version is not None:
        attrs["version"] = Expr("var.version")
    if config.body is not None:
        attrs["body"] = Expr("var.body")
    if config.fail_on_warnings is not None:
        attrs["fail_on_warnings"] = Expr("var.fail_on_warnings")

    # Mutual TLS authentication block
    mutual_tls = getattr(config, "mutual_tls_authentication", None)
    if mutual_tls and mutual_tls.get("truststore_uri"):
        mutual_tls_block: dict = {
            "truststore_uri": mutual_tls["truststore_uri"],
        }
        if mutual_tls.get("truststore_version"):
            mutual_tls_block["truststore_version"] = mutual_tls["truststore_version"]
        attrs["mutual_tls_authentication"] = mutual_tls_block

    return r.render_resource("aws_apigatewayv2_api", instance.name, attrs)


def render_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Variable blocks this concern contributes."""
    parts: list[str] = [
        # Required fields — no default
        r.render_variable("api_name", "string", "Name of the API Gateway"),
        r.render_variable("protocol_type", "string", "API protocol type"),
    ]
    # ─── General optional fields ─────────────────────────────────────────
    if config.description is not None:
        parts.append(
            r.render_variable(
                "description",
                "string",
                "Description of the API",
                default=config.description,
            )
        )
    if config.api_key_selection_expression is not None:
        parts.append(
            r.render_variable(
                "api_key_selection_expression",
                "string",
                "API key selection expression for the API",
                default=config.api_key_selection_expression,
            )
        )
    if config.ip_address_type is not None:
        parts.append(
            r.render_variable(
                "ip_address_type",
                "string",
                "IP address type for the API endpoint",
                default=config.ip_address_type,
            )
        )
    if config.version is not None:
        parts.append(
            r.render_variable(
                "version",
                "string",
                "Version identifier for the API",
                default=config.version,
            )
        )
    if config.body is not None:
        parts.append(
            r.render_variable(
                "body",
                "string",
                "OpenAPI specification body for the API",
                default=config.body,
            )
        )
    if config.fail_on_warnings is not None:
        parts.append(
            r.render_variable(
                "fail_on_warnings",
                "bool",
                "Whether to roll back the API creation when a warning is encountered",
                default=config.fail_on_warnings,
            )
        )
    return parts


def render_metadata_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Tags are emitted after every other concern, matching the original layout."""
    parts: list[str] = []
    # ─── Metadata fields ──────────────────────────────────────────────────
    if config.tags is not None:
        parts.append(
            r.render_variable(
                "tags",
                "map(string)",
                "Tags to apply to the API Gateway",
            )
        )
    return parts
