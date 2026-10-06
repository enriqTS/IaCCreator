"""API-owned Cognito JWT authorizers shared by selected HTTP routes."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.cognito_api_gateway import CognitoApiGatewayConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.cognito_api_gateway_bindings import (
    resolve_cognito_jwt_bindings,
)


class CognitoApiGatewayHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        config = CognitoApiGatewayConfig.model_validate(connection.connection_config)
        bindings = resolve_cognito_jwt_bindings(connection.target_name, project)
        if bindings[(config.method, config.path)].scopes:
            return []
        return [
            ConnectionIssue(
                severity="warning",
                message="No authorization scopes are required: valid Cognito ID tokens and access tokens can authorize this route. Configure scopes when the route should require access tokens; JWT authentication does not enforce user ownership in the backend.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        gateway = connection.target_name
        peers = [
            item
            for item in project.connections
            if item.target_name == gateway
            and item.source_service == ServiceType.COGNITO
            and item.connection_type == "authenticates"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        bindings = resolve_cognito_jwt_bindings(gateway, project)
        self._find_instance(gateway, project).config._cognito_jwt_routes = bindings
        result = ConnectionContribution()
        pools = {binding.pool_name: binding for binding in bindings.values()}
        for name, binding in sorted(pools.items()):
            prefix = f"cognito_{name}"
            result.inputs.extend(
                [
                    ModuleInput(
                        module=gateway,
                        name=f"{prefix}_endpoint",
                        value=f"module.{name}.endpoint",
                    ),
                    ModuleInput(
                        module=gateway,
                        name=f"{prefix}_client_id",
                        value=f"module.{name}.client_id",
                    ),
                ]
            )
            authorizer = self._renderer.render_resource(
                "aws_apigatewayv2_authorizer",
                binding.authorizer_resource,
                {
                    "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                    "name": binding.authorizer_resource,
                    "authorizer_type": "JWT",
                    "identity_sources": ["$request.header.Authorization"],
                    "jwt_configuration": {
                        "issuer": Expr(f'format("https://%s", var.{prefix}_endpoint)'),
                        "audience": [Expr(f"var.{prefix}_client_id")],
                    },
                },
            )
            result.resources.append(
                self._resource(gateway, f"cognito_authorizer_{name}.tf", authorizer)
            )
        return result
