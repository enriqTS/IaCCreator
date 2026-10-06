"""Resolve JWT route bindings independently of connection processing order."""

from app.exceptions import InvalidConnectionConfigError
from app.models.api_gateway_authentication import CognitoJwtRouteBinding
from app.models.connection_configs.cognito_api_gateway import CognitoApiGatewayConfig
from app.models.input_models import ServiceType
from app.models.input_models.api_gateway_route import route_dicts
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


def reject_binding(connection: ConnectionIR, field: str, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": (field,), "msg": message}],
    )


def _matching_routes(connection, config, gateway, project) -> list[dict]:
    matches = []
    manual_integrations = {item.get("name") for item in gateway.integrations or []}
    managed_routes = []
    for peer in project.connections:
        if peer.source_name != connection.target_name:
            continue
        if peer.connection_type not in {"route_handler", "starts_execution"}:
            continue
        for route in peer.connection_config.get("routes", []):
            if route.get("path") != config.path or config.method not in {
                method.upper() for method in route.get("methods", ["ANY"])
            }:
                continue
            if peer.connection_type == "starts_execution":
                reject_binding(
                    connection,
                    "path",
                    "Workflow routes require AWS_IAM authorization and cannot use Cognito JWT authorization",
                )
            managed_routes.append(route)
    for route in route_dicts(gateway.routes) or []:
        if route.get("path") != config.path or config.method not in route.get(
            "methods", ["ANY"]
        ):
            continue
        if (
            route.get("integration_name")
            and route["integration_name"] not in manual_integrations
            and not managed_routes
        ):
            reject_binding(
                connection,
                "path",
                "Selected route has no generated integration connection",
            )
        matches.append(route)
    inherited = matches[0] if matches else {}
    return matches + [{**inherited, **route} for route in managed_routes]


def resolve_cognito_jwt_bindings(
    gateway_name: str, project: ProjectIR
) -> dict[tuple[str, str], CognitoJwtRouteBinding]:
    bindings = {}
    peers = [
        item
        for item in project.connections
        if item.target_name == gateway_name
        and item.source_service == ServiceType.COGNITO
        and item.target_service == ServiceType.API_GATEWAY
        and item.connection_type == "authenticates"
    ]
    if not peers:
        return bindings
    gateway = BaseConnectionHandler._find_instance(gateway_name, project).config
    if gateway.protocol_type != "HTTP" or gateway.body:
        reject_binding(
            peers[0],
            "protocol_type",
            "Cognito JWT connections require an HTTP API without an OpenAPI body",
        )
    for connection in peers:
        config = CognitoApiGatewayConfig.model_validate(connection.connection_config)
        pool = BaseConnectionHandler._find_instance(
            connection.source_name, project
        ).config
        if not pool.create_client:
            reject_binding(
                connection,
                "create_client",
                "Cognito JWT authentication requires a generated application client",
            )
        matches = _matching_routes(connection, config, gateway, project)
        if not matches:
            reject_binding(
                connection,
                "path",
                "Select an existing HTTP route with the exact configured method and path",
            )
        key = (config.method, config.path)
        for route in matches:
            auth_type = route.get("authorization_type", gateway.authorization_type)
            if route.get("authorizer_name") or auth_type not in {None, "NONE", "JWT"}:
                reject_binding(
                    connection,
                    "path",
                    "Selected route already requires another authorizer or IAM authorization",
                )
            if route.get("api_key_required") or gateway.api_key_required:
                reject_binding(
                    connection, "path", "HTTP JWT routes cannot require API keys"
                )
            scopes = (
                config.authorization_scopes.split(",")
                if config.authorization_scopes
                else []
                if config.authorization_scopes == ""
                else route.get("authorization_scopes", gateway.authorization_scopes)
                or []
            )
            binding = CognitoJwtRouteBinding(
                connection.source_name, tuple(sorted(set(scopes)))
            )
            previous = bindings.get(key)
            if previous is not None and previous != binding:
                reject_binding(
                    connection,
                    "path",
                    "A route can have only one Cognito pool and one scope configuration",
                )
            bindings[key] = binding
    return bindings
