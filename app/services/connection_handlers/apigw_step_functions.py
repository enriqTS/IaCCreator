"""HTTP API routes start a connected Step Functions workflow."""

import hashlib

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.apigw_step_functions import (
    ApiGatewayStepFunctionsConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class ApiGatewayStepFunctionsHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The HTTP route starts the workflow asynchronously. Protect the route with IAM authorization and use execution history to inspect results.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = ApiGatewayStepFunctionsConfig.model_validate(
            connection.connection_config
        )
        gateway, workflow = connection.source_name, connection.target_name
        api = self._find_instance(gateway, project)
        self._check_connection(connection, project, config, api)
        prefix = safe_identifier(workflow)
        role = f"{prefix}_execution"
        variable = f"{prefix}_state_machine_arn"
        render = self._renderer.render_resource
        policy = self._renderer.render_json_policy
        resources = [
            render(
                "aws_iam_role",
                role,
                {
                    "name_prefix": "apigw-workflow-",
                    "assume_role_policy": policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "Service": "apigateway.amazonaws.com"
                                    },
                                    "Action": "sts:AssumeRole",
                                }
                            ],
                        }
                    ),
                },
            ),
            render(
                "aws_iam_role_policy",
                role,
                {
                    "role": Expr(f"aws_iam_role.{role}.id"),
                    "policy": policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["states:StartExecution"],
                                    "Resource": [Expr(f"var.{variable}")],
                                }
                            ],
                        }
                    ),
                },
            ),
            render(
                "aws_apigatewayv2_integration",
                f"{prefix}_workflow",
                {
                    "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                    "integration_type": "AWS_PROXY",
                    "integration_subtype": "StepFunctions-StartExecution",
                    "payload_format_version": "1.0",
                    "credentials_arn": Expr(f"aws_iam_role.{role}.arn"),
                    "request_parameters": Expr(
                        self._renderer.render_expression(
                            {
                                "StateMachineArn": Expr(f"var.{variable}"),
                                "Input": "$request.body",
                            }
                        )
                    ),
                    "depends_on": Expr(f"[aws_iam_role_policy.{role}]"),
                },
            ),
        ]
        for route in config.routes:
            path = route["path"]
            token = hashlib.sha256(path.encode()).hexdigest()[:12]
            route_name = f"{prefix}_workflow_{token}"
            attrs = {
                "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                "route_key": f"POST {path}",
                "target": Expr(
                    f'"integrations/${{aws_apigatewayv2_integration.{prefix}_workflow.id}}"'
                ),
                "authorization_type": "AWS_IAM",
            }
            if route.get("api_key_required") or api.config.api_key_required:
                attrs["api_key_required"] = True
            resources.append(render("aws_apigatewayv2_route", route_name, attrs))
            if route.get("route_response_key"):
                resources.append(
                    render(
                        "aws_apigatewayv2_route_response",
                        f"{route_name}_response",
                        {
                            "api_id": Expr(f"aws_apigatewayv2_api.{gateway}.id"),
                            "route_id": Expr(f"aws_apigatewayv2_route.{route_name}.id"),
                            "route_response_key": route["route_response_key"],
                        },
                    )
                )
            api.config._managed_connection_routes.add(("POST", path))
        return ConnectionContribution(
            inputs=[
                self._input(
                    gateway,
                    workflow,
                    "state_machine_arn",
                    f"module.{workflow}.state_machine_arn",
                    "ARN of the workflow started by this HTTP API",
                )
            ],
            resources=[
                self._resource(gateway, f"workflow_{workflow}.tf", "\n".join(resources))
            ],
        )

    def _check_connection(
        self,
        connection: ConnectionIR,
        project: ProjectIR,
        config: ApiGatewayStepFunctionsConfig,
        api,
    ) -> None:
        problems = []
        if api.config.protocol_type != "HTTP" or api.config.body:
            problems.append(
                {
                    "loc": ("protocol_type",),
                    "msg": "Use an HTTP API without an OpenAPI body",
                }
            )
        if not config.routes:
            problems.append(
                {
                    "loc": ("routes",),
                    "msg": "Bind at least one POST route to the workflow",
                }
            )
        seen = set()
        for route in config.routes:
            path = route.get("path")
            if not isinstance(path, str) or not path.startswith("/"):
                problems.append({"loc": ("routes",), "msg": "Routes need an HTTP path"})
                continue
            if route.get("methods") != ["POST"]:
                problems.append(
                    {"loc": ("routes",), "msg": "Workflow routes must use POST only"}
                )
            if path in seen:
                problems.append(
                    {"loc": ("routes",), "msg": "Route paths must be unique"}
                )
            seen.add(path)
        for route in api.config.routes or []:
            if route.path not in seen:
                continue
            if route.authorizer_name or route.authorization_type not in {
                None,
                "AWS_IAM",
            }:
                problems.append(
                    {
                        "loc": ("routes",),
                        "msg": "Workflow routes must use AWS_IAM authorization",
                    }
                )
        for peer in project.connections:
            if peer is connection or peer.source_name != connection.source_name:
                continue
            if (
                peer.connection_type == "starts_execution"
                and peer.target_name == connection.target_name
            ):
                if peer.connection_config != connection.connection_config:
                    problems.append(
                        {"loc": ("routes",), "msg": "Use one connection per workflow"}
                    )
                continue
            if peer.connection_type not in {"starts_execution", "route_handler"}:
                continue
            for route in peer.connection_config.get("routes", []):
                if route.get("path") in seen and "POST" in route.get("methods", []):
                    problems.append(
                        {
                            "loc": ("routes",),
                            "msg": "POST route already belongs to another connection",
                        }
                    )
        if problems:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                problems,
            )
