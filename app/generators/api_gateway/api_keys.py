"""API keys and their usage plans."""

from app.generators.api_gateway._support import sanitize_route_name
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_api_keys(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate API key resources based on protocol type and configured keys.

    - If `api_keys` list is configured, generates one resource per key:
      - HTTP protocol: emits `aws_api_gateway_api_key` (REST v1 type) with a warning comment
      - WEBSOCKET protocol: emits `aws_apigatewayv2_api_key` resources
    - Falls back to legacy behavior (single key) when only `api_key_required` is set
      without an explicit `api_keys` list.
    """
    api_keys = getattr(config, "api_keys", None)

    # Use the api_keys list if available
    if api_keys:
        protocol_type = config.protocol_type or "HTTP"
        parts: list[str] = []

        if protocol_type == "HTTP":
            # HTTP APIs do not natively support API keys — emit REST v1 resource type
            # with a warning comment
            comment = (
                "# NOTE: HTTP APIs do not natively support API keys. "
                "Consider using a Lambda authorizer.\n"
            )
            parts.append(comment)
            for key in api_keys:
                key_name = key.get("name", f"{instance.name}-api-key")
                sanitized_key_name = sanitize_route_name(key_name)
                resource_name = f"{instance.name}_{sanitized_key_name}_api_key"
                attrs: dict = {
                    "name": key_name,
                }
                if key.get("description"):
                    attrs["description"] = key["description"]
                if key.get("value"):
                    attrs["value"] = key["value"]
                parts.append(
                    r.render_resource("aws_api_gateway_api_key", resource_name, attrs)
                )
        else:
            # WEBSOCKET — api_key_selection_expression is set on the API resource
            # (handled in _generate_api_resource), generate aws_apigatewayv2_api_key blocks
            for key in api_keys:
                key_name = key.get("name", f"{instance.name}-api-key")
                sanitized_key_name = sanitize_route_name(key_name)
                resource_name = f"{instance.name}_{sanitized_key_name}_api_key"
                attrs = {
                    "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                    "name": key_name,
                }
                if key.get("description"):
                    attrs["description"] = key["description"]
                if key.get("value"):
                    attrs["value"] = key["value"]
                parts.append(
                    r.render_resource("aws_apigatewayv2_api_key", resource_name, attrs)
                )

        return "\n".join(parts)

    # Legacy fallback: single key when api_key_required is set without api_keys list
    if not config.api_key_required:
        return ""

    attrs = {
        "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
        "name": f"{instance.name}-api-key",
    }
    return r.render_resource(
        "aws_apigatewayv2_api_key", f"{instance.name}_api_key", attrs
    )
