"""API Gateway → Lambda connection handler.

The gateway module owns the integration, routes, authorizer and invoke permission, so
values only ever flow Lambda → gateway and Terraform sees no dependency cycle.
"""

import re

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


def _sanitize_path(path: str) -> str:
    """Sanitize a route path into a Terraform name, keeping distinct paths distinct."""
    # Path parameters are marked so "/users/{id}" cannot collide with "/users/id"
    result = re.sub(r"\{([^}]*)\}", r"var_\1", path)
    result = re.sub(r"[^A-Za-z0-9_]", "_", result)
    result = re.sub(r"_+", "_", result)
    return result.strip("_")


class ApiGatewayLambdaHandler(BaseConnectionHandler):
    """Handles API Gateway → Lambda connections in both route_handler and authorizer roles."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        if connection.connection_type == "authorizer":
            return self._handle_authorizer(connection)
        return self._handle_route_handler(connection)

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        """A route handler with no route deploys an integration nothing can reach."""
        if connection.connection_type == "authorizer":
            return []
        if connection.connection_config.get("routes"):
            return []
        return [
            ConnectionIssue(
                severity="warning",
                message=(
                    f"No route on {connection.source_name} points at "
                    f"{connection.target_name}, so the integration deploys but the "
                    f"function can never be invoked."
                ),
            )
        ]

    def _lambda_wiring(self, gateway: str, function: str) -> ConnectionContribution:
        """Outputs and inputs every role needs to reach the target Lambda."""
        return ConnectionContribution(
            outputs=[
                self._output(
                    function,
                    "invoke_arn",
                    f"aws_lambda_function.{function}.invoke_arn",
                    "Invocation ARN for API Gateway integrations",
                ),
                self._output(
                    function,
                    "function_name",
                    f"aws_lambda_function.{function}.function_name",
                    "Name of the Lambda function",
                ),
            ],
            inputs=[
                self._input(
                    gateway,
                    function,
                    "invoke_arn",
                    f"module.{function}.invoke_arn",
                    f"Invocation ARN of the {function} function",
                ),
                self._input(
                    gateway,
                    function,
                    "function_name",
                    f"module.{function}.function_name",
                    f"Name of the {function} function",
                ),
            ],
        )

    def _handle_route_handler(self, connection: ConnectionIR) -> ConnectionContribution:
        """Emit the shared integration, one route per method-path pair, and the permission."""
        gateway = connection.source_name
        function = connection.target_name
        prefix = safe_identifier(function)
        integration_name = f"{prefix}_integration"

        integration_attrs: dict[str, object] = {
            "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
            "integration_type": connection.connection_config.get(
                "integration_type", "AWS_PROXY"
            ),
            "integration_uri": Expr(f"var.{prefix}_invoke_arn"),
            "payload_format_version": connection.connection_config.get(
                "payload_format_version", "2.0"
            ),
        }
        vpc_link_name = connection.connection_config.get("vpc_link_name")
        if vpc_link_name:
            integration_attrs["connection_type"] = "VPC_LINK"
            integration_attrs["connection_id"] = Expr(
                f"aws_apigatewayv2_vpc_link.{vpc_link_name}.id"
            )

        contribution = self._lambda_wiring(gateway, function)
        contribution.resources.append(
            self._resource(
                gateway,
                f"integration_{function}.tf",
                self._renderer.render_resource(
                    "aws_apigatewayv2_integration", integration_name, integration_attrs
                ),
            )
        )

        for route in connection.connection_config.get("routes", []):
            path = route["path"]
            sanitized = _sanitize_path(path)
            for method in route["methods"]:
                verb = method.upper()
                route_name = f"{prefix}_route_{verb.lower()}_{sanitized}"
                route_attrs: dict[str, object] = {
                    "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                    "route_key": f"{verb} {path}",
                    "target": Expr(
                        f'"integrations/${{aws_apigatewayv2_integration.{integration_name}.id}}"'
                    ),
                }
                if route.get("api_key_required"):
                    route_attrs["api_key_required"] = True

                content = self._renderer.render_resource(
                    "aws_apigatewayv2_route", route_name, route_attrs
                )
                if route.get("route_response_key"):
                    content += "\n" + self._renderer.render_resource(
                        "aws_apigatewayv2_route_response",
                        f"{route_name}_response",
                        {
                            "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                            "route_id": Expr(f"aws_apigatewayv2_route.{route_name}.id"),
                            "route_response_key": route["route_response_key"],
                        },
                    )
                contribution.resources.append(
                    self._resource(
                        gateway,
                        f"route_{function}_{verb.lower()}_{sanitized}.tf",
                        content,
                    )
                )

        contribution.resources.append(
            self._resource(
                gateway,
                f"permission_{function}.tf",
                self._renderer.render_resource(
                    "aws_lambda_permission",
                    f"{prefix}_permission",
                    {
                        "statement_id": f"AllowAPIGatewayInvoke{prefix}",
                        "action": "lambda:InvokeFunction",
                        "function_name": Expr(f"var.{prefix}_function_name"),
                        "principal": "apigateway.amazonaws.com",
                        "source_arn": Expr(
                            f'"${{aws_apigatewayv2_api.{gateway}.execution_arn}}/*/*"'
                        ),
                    },
                ),
            )
        )
        return contribution

    def _handle_authorizer(self, connection: ConnectionIR) -> ConnectionContribution:
        """Emit a REQUEST authorizer backed by the Lambda, plus its invoke permission."""
        gateway = connection.source_name
        function = connection.target_name
        prefix = safe_identifier(function)

        contribution = self._lambda_wiring(gateway, function)
        contribution.resources.append(
            self._resource(
                gateway,
                f"authorizer_{function}.tf",
                self._renderer.render_resource(
                    "aws_apigatewayv2_authorizer",
                    f"{prefix}_authorizer",
                    {
                        "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                        "name": connection.connection_config.get(
                            "authorizer_name", function
                        ),
                        "authorizer_type": "REQUEST",
                        "authorizer_uri": Expr(f"var.{prefix}_invoke_arn"),
                        "authorizer_payload_format_version": connection.connection_config.get(
                            "payload_format_version", "2.0"
                        ),
                    },
                ),
            )
        )
        contribution.resources.append(
            self._resource(
                gateway,
                f"authorizer_permission_{function}.tf",
                self._renderer.render_resource(
                    "aws_lambda_permission",
                    f"{prefix}_authorizer_permission",
                    {
                        "statement_id": f"AllowAPIGatewayAuthorizer{prefix}",
                        "action": "lambda:InvokeFunction",
                        "function_name": Expr(f"var.{prefix}_function_name"),
                        "principal": "apigateway.amazonaws.com",
                        "source_arn": Expr(
                            f'"${{aws_apigatewayv2_api.{gateway}.execution_arn}}/authorizers/*"'
                        ),
                    },
                ),
            )
        )
        return contribution
