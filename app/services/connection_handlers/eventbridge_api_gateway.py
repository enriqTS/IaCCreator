"""EventBridge invokes one deployed IAM-authorized HTTP API route."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_api_gateway import (
    EventBridgeApiGatewayConfig,
)
from app.models.input_models.api_gateway_route import route_dicts
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeApiGatewayHandler(EventBridgeRoleTargetHandler):
    config_model = EventBridgeApiGatewayConfig

    def __init__(self):
        super().__init__(
            "api",
            "execute-api:Invoke",
            "execution_arn",
            "Invokes the selected IAM-authorized HTTP API route. Configure route integration, retries, dead-letter handling, and monitoring separately.",
        )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = self.config_model.model_validate(connection.connection_config)
        gateway = self._find_instance(connection.target_name, project).config
        stages = gateway.stages or [{"name": "$default"}]
        routes = route_dicts(gateway.routes) or []
        matched = [
            route
            for route in routes
            if route.get("path") == config.path
            and (
                config.method in route.get("methods", ["ANY"])
                or "ANY" in route.get("methods", ["ANY"])
            )
            and route.get("authorization_type", gateway.authorization_type) == "AWS_IAM"
            and not route.get("authorizer_name")
            and not route.get("api_key_required")
            and not gateway.api_key_required
            and route.get("integration_name")
            in {integration.get("name") for integration in gateway.integrations or []}
        ]
        if (
            gateway.protocol_type != "HTTP"
            or gateway.disable_execute_api_endpoint
            or not any(
                stage.get("name", "$default") == config.stage for stage in stages
            )
            or not matched
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("path",),
                        "msg": "Select a deployed IAM-authorized HTTP POST route and stage with the execute-api endpoint enabled",
                    }
                ],
            )
        return super().handle(connection, project)

    def grant_resource(self, variable: str, config: EventBridgeApiGatewayConfig) -> str:
        return "${var." + variable + "}/" + self._suffix(config)

    def output_name(self, destination: str) -> str:
        return f"{destination}_execution_arn"

    def target_arn(self, variable: str, config: EventBridgeApiGatewayConfig) -> Expr:
        return Expr('"${var.' + variable + "}/" + self._suffix(config) + '"')

    @staticmethod
    def _suffix(config: EventBridgeApiGatewayConfig) -> str:
        return f"{config.stage}/{config.method}/{config.path.lstrip('/')}"
