"""Route lookup and the rules that shape a route's attributes."""

from app.generators.hcl_renderer import Expr
from app.models.input_models.api_gateway_config import ApiGatewayConfig


def find_ws_route_integration(
    route_key: str, routes: list[dict] | None, instance_name: str
) -> str | None:
    """Find the integration target for a WebSocket special route."""
    if not routes:
        return None
    for route_cfg in routes:
        cfg_route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
        if cfg_route_key == route_key:
            integration_name = route_cfg.get("integration_name")
            if integration_name:
                return (
                    f"integrations/${{aws_apigatewayv2_integration."
                    f"{instance_name}_{integration_name}_integration.id}}"
                )
    return None


def find_route_cfg(routes: list[dict] | None, route_key: str) -> dict | None:
    """Find a route config dict by route_key from the routes list."""
    if not routes:
        return None
    for route_cfg in routes:
        cfg_route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
        if cfg_route_key == route_key:
            return route_cfg
    return None


def apply_authorization(
    attrs: dict,
    routes: list[dict] | None,
    route_key: str,
    authorizer_map: dict[str, dict],
    instance_name: str,
    is_connect: bool = False,
) -> None:
    """Apply authorization attributes to a route if configured.

    For WebSocket, only $connect gets authorization (is_connect=True).
    """
    if not routes:
        return
    for route_cfg in routes:
        cfg_route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
        if cfg_route_key == route_key:
            authorizer_name = route_cfg.get("authorizer_name")
            if authorizer_name and authorizer_name in authorizer_map:
                auth_cfg = authorizer_map[authorizer_name]
                auth_type = auth_cfg.get("type", "JWT")
                if auth_type in ("JWT", "COGNITO_USER_POOLS"):
                    attrs["authorization_type"] = "JWT"
                elif auth_type == "REQUEST":
                    attrs["authorization_type"] = "CUSTOM"
                attrs["authorizer_id"] = Expr(
                    f"aws_apigatewayv2_authorizer."
                    f"{instance_name}_{authorizer_name}_authorizer.id"
                )
            break


def apply_route_optional_fields(
    attrs: dict,
    route_cfg: dict | None,
    routes: list[dict] | None,
    route_key: str,
    config: "ApiGatewayConfig",
) -> None:
    """Apply optional route fields from route dict or top-level config TerraformFields.

    Adds authorization_type, authorization_scopes, operation_name,
    model_selection_expression, and route_response_selection_expression
    when they are set (per-route dict takes precedence over config-level fields).
    Does NOT override authorization_type if already set by authorizer logic.
    """
    # authorization_type — only if not already set by the authorizer logic
    if "authorization_type" not in attrs:
        auth_type = (route_cfg or {}).get("authorization_type")
        if auth_type is None:
            auth_type = getattr(config, "authorization_type", None)
        if auth_type is not None:
            attrs["authorization_type"] = auth_type

    # authorization_scopes
    auth_scopes = (route_cfg or {}).get("authorization_scopes")
    if auth_scopes is None:
        auth_scopes = getattr(config, "authorization_scopes", None)
    if auth_scopes is not None:
        attrs["authorization_scopes"] = auth_scopes

    # operation_name
    op_name = (route_cfg or {}).get("operation_name")
    if op_name is None:
        op_name = getattr(config, "operation_name", None)
    if op_name is not None:
        attrs["operation_name"] = op_name

    # model_selection_expression
    model_sel = (route_cfg or {}).get("model_selection_expression")
    if model_sel is None:
        model_sel = getattr(config, "model_selection_expression", None)
    if model_sel is not None:
        attrs["model_selection_expression"] = model_sel

    # route_response_selection_expression
    route_resp_sel = (route_cfg or {}).get("route_response_selection_expression")
    if route_resp_sel is None:
        route_resp_sel = getattr(config, "route_response_selection_expression", None)
    if route_resp_sel is not None:
        attrs["route_response_selection_expression"] = route_resp_sel
