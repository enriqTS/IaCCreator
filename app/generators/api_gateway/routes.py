"""Routes, their authorization, and their optional per-route settings."""

from app.generators.api_gateway._route_rules import (
    apply_authorization,
    apply_route_optional_fields,
    find_route_cfg,
    find_ws_route_integration,
)
from app.generators.api_gateway._support import sanitize_route_name
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_routes(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_route resources for the API Gateway instance.

    For HTTP APIs:
      - Produces a route for each configured entry, or a $default route if none configured.
    For WebSocket APIs:
      - Always produces $connect, $disconnect, $default routes, plus any custom routes.
    Routes referencing authorizers get authorization_type and authorizer_id.
    For WebSocket, only $connect gets authorization attributes (per AWS docs).
    If api_key_required is True, all routes get api_key_required = true.
    """
    protocol_type = config.protocol_type or "HTTP"
    is_websocket = protocol_type == "WEBSOCKET"

    # Build a lookup of authorizer names to their configs for authorization_type resolution
    authorizer_map: dict[str, dict] = {}
    authorizers = getattr(config, "authorizers", None)
    if authorizers:
        for auth in authorizers:
            authorizer_map[auth["name"]] = auth

    # Build a lookup of integration names for target resolution
    integration_names: set[str] = set()
    integrations = getattr(config, "integrations", None)
    if integrations:
        # An unnamed integration cannot be referenced, and the validator rejects it
        for integ in integrations:
            name = integ.get("name")
            if name:
                integration_names.add(name)

    parts: list[str] = []
    routes = getattr(config, "routes", None)

    if is_websocket:
        # WebSocket: always generate special routes + custom routes
        ws_special_routes = ["$connect", "$disconnect", "$default"]
        custom_routes: list[dict] = []
        if routes:
            custom_routes = routes

        for route_key in ws_special_routes:
            route_name = sanitize_route_name(route_key)
            resource_name = f"{instance.name}_{route_name}_route"
            attrs: dict = {
                "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                "route_key": route_key,
            }

            # Target integration if available (use $default integration or named)
            target_integration = find_ws_route_integration(
                route_key, routes, instance.name
            )
            if target_integration:
                attrs["target"] = target_integration

            # Authorization only on $connect
            if route_key == "$connect":
                apply_authorization(
                    attrs,
                    routes,
                    route_key,
                    authorizer_map,
                    instance.name,
                    is_connect=True,
                )

            # API key required — per-route or config-level
            ws_route_cfg = find_route_cfg(routes, route_key)
            if (
                ws_route_cfg and ws_route_cfg.get("api_key_required")
            ) or config.api_key_required:
                attrs["api_key_required"] = True

            # New optional route fields from TerraformField config
            apply_route_optional_fields(attrs, None, routes, route_key, config)

            parts.append(
                r.render_resource("aws_apigatewayv2_route", resource_name, attrs)
            )

            # Route response generation for WebSocket special routes
            if ws_route_cfg:
                route_response_key = ws_route_cfg.get("route_response_key")
                if route_response_key:
                    response_resource_name = (
                        f"{instance.name}_{route_name}_route_response"
                    )
                    response_attrs = {
                        "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                        "route_id": Expr(f"aws_apigatewayv2_route.{resource_name}.id"),
                        "route_response_key": route_response_key,
                    }
                    parts.append(
                        r.render_resource(
                            "aws_apigatewayv2_route_response",
                            response_resource_name,
                            response_attrs,
                        )
                    )

        # Custom WebSocket routes (non-special)
        for route_cfg in custom_routes:
            route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
            if route_key in ws_special_routes:
                continue  # Already handled above
            route_name = sanitize_route_name(route_key)
            resource_name = f"{instance.name}_{route_name}_route"
            attrs = {
                "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                "route_key": route_key,
            }

            # Target integration
            integration_name = route_cfg.get("integration_name")
            if integration_name and integration_name in integration_names:
                attrs["target"] = (
                    f"integrations/${{aws_apigatewayv2_integration."
                    f"{instance.name}_{integration_name}_integration.id}}"
                )

            # WebSocket non-$connect routes do NOT get authorization (Property 4)

            # API key required — per-route or config-level
            if route_cfg.get("api_key_required") or config.api_key_required:
                attrs["api_key_required"] = True

            # New optional route fields from TerraformField config
            apply_route_optional_fields(attrs, route_cfg, routes, route_key, config)

            parts.append(
                r.render_resource("aws_apigatewayv2_route", resource_name, attrs)
            )

            # Route response generation for custom WebSocket routes
            route_response_key = route_cfg.get("route_response_key")
            if route_response_key:
                response_resource_name = f"{instance.name}_{route_name}_route_response"
                response_attrs = {
                    "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                    "route_id": Expr(f"aws_apigatewayv2_route.{resource_name}.id"),
                    "route_response_key": route_response_key,
                }
                parts.append(
                    r.render_resource(
                        "aws_apigatewayv2_route_response",
                        response_resource_name,
                        response_attrs,
                    )
                )

    else:
        # HTTP API
        if routes:
            for route_cfg in routes:
                # Skip connection-derived routes (no matching integration in config.integrations).
                # These are handled by ApiGatewayLambdaHandler which generates both the route
                # and its integration target properly. Only emit routes here that have a
                # manually-declared integration in config.integrations.
                integration_name = route_cfg.get("integration_name")
                if integration_name and integration_name not in integration_names:
                    continue

                methods = route_cfg.get("methods", ["ANY"])
                path = route_cfg.get("path", "/")

                for method in methods:
                    route_key = f"{method} {path}"
                    route_name = sanitize_route_name(f"{method}_{path}")
                    resource_name = f"{instance.name}_{route_name}_route"

                    attrs = {
                        "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                        "route_key": route_key,
                    }

                    # Target integration (only for manually-declared integrations)
                    if integration_name and integration_name in integration_names:
                        attrs["target"] = (
                            f"integrations/${{aws_apigatewayv2_integration."
                            f"{instance.name}_{integration_name}_integration.id}}"
                        )

                    # Authorization
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
                            f"{instance.name}_{authorizer_name}_authorizer.id"
                        )

                    # API key required — per-route or config-level
                    if route_cfg.get("api_key_required") or config.api_key_required:
                        attrs["api_key_required"] = True

                    # New optional route fields from TerraformField config
                    apply_route_optional_fields(
                        attrs, route_cfg, routes, route_key, config
                    )

                    parts.append(
                        r.render_resource(
                            "aws_apigatewayv2_route", resource_name, attrs
                        )
                    )

                    # Route response generation when route_response_key is present
                    route_response_key = route_cfg.get("route_response_key")
                    if route_response_key:
                        response_resource_name = (
                            f"{instance.name}_{route_name}_route_response"
                        )
                        response_attrs = {
                            "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                            "route_id": Expr(
                                f"aws_apigatewayv2_route.{resource_name}.id"
                            ),
                            "route_response_key": route_response_key,
                        }
                        parts.append(
                            r.render_resource(
                                "aws_apigatewayv2_route_response",
                                response_resource_name,
                                response_attrs,
                            )
                        )
        else:
            # No routes configured — generate $default route
            resource_name = f"{instance.name}_default_route"
            attrs = {
                "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
                "route_key": "$default",
            }

            # API key required
            if config.api_key_required:
                attrs["api_key_required"] = True

            # New optional route fields from TerraformField config
            apply_route_optional_fields(attrs, None, routes, "$default", config)

            parts.append(
                r.render_resource("aws_apigatewayv2_route", resource_name, attrs)
            )

    return "\n".join(parts)


def render_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Variable blocks this concern contributes."""
    parts: list[str] = []
    # ─── Routes fields ────────────────────────────────────────────────────
    if config.cors_configuration is not None:
        parts.append(
            r.render_variable(
                "cors_configuration",
                "map(string)",
                "CORS configuration for the API",
            )
        )
    if config.disable_execute_api_endpoint is not None:
        parts.append(
            r.render_variable(
                "disable_execute_api_endpoint",
                "bool",
                "Disable the default execute-api endpoint",
                default=config.disable_execute_api_endpoint,
            )
        )
    # route_selection_expression — only when protocol_type is WEBSOCKET (visible_when)
    if config.protocol_type == "WEBSOCKET":
        if config.route_selection_expression is not None:
            parts.append(
                r.render_variable(
                    "route_selection_expression",
                    "string",
                    "Route selection expression for WebSocket APIs",
                    default=config.route_selection_expression,
                )
            )
    if config.authorization_type is not None:
        parts.append(
            r.render_variable(
                "authorization_type",
                "string",
                "Authorization type for the route",
                default=config.authorization_type,
            )
        )
    if config.authorization_scopes is not None:
        parts.append(
            r.render_variable(
                "authorization_scopes",
                "list(string)",
                "Authorization scopes for the route",
                default=config.authorization_scopes,
            )
        )
    if config.operation_name is not None:
        parts.append(
            r.render_variable(
                "operation_name",
                "string",
                "Operation name for the route",
                default=config.operation_name,
            )
        )
    if config.model_selection_expression is not None:
        parts.append(
            r.render_variable(
                "model_selection_expression",
                "string",
                "Model selection expression for the route",
                default=config.model_selection_expression,
            )
        )
    if config.route_response_selection_expression is not None:
        parts.append(
            r.render_variable(
                "route_response_selection_expression",
                "string",
                "Route response selection expression",
                default=config.route_response_selection_expression,
            )
        )
    return parts
