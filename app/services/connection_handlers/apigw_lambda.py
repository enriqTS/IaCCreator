"""API Gateway → Lambda connection handler.

Supports two connection roles dispatched via ``connection_config["connection_role"]``:

- **route_handler** (default): generates a single ``aws_apigatewayv2_integration``
  shared across all routes, one ``aws_apigatewayv2_route`` per entry in the
  ``routes`` array, and one ``aws_lambda_permission``.
- **authorizer**: generates an ``aws_apigatewayv2_authorizer`` resource (type REQUEST)
  and an ``aws_lambda_permission`` for authorizer invocation. Does NOT generate
  integration or route resources.

Multi-route support via ``connection_config["routes"]``:
    Each entry is a dict with ``method`` (e.g. "GET") and ``path`` (e.g. "/users/{id}").
    Route resource names use path sanitization: ``/``, ``{``, ``}`` are replaced with
    ``_``, consecutive underscores are collapsed, and leading/trailing underscores are
    stripped.

Enhanced integration configuration:
    - ``integration_type``: defaults to "AWS_PROXY"
    - ``payload_format_version``: defaults to "2.0"
    - ``vpc_link_name``: when present, adds ``connection_type="VPC_LINK"`` and
      ``connection_id`` referencing the named VPC link

Generated resources (route_handler role):
    - aws_apigatewayv2_integration (1 per connection)
    - aws_apigatewayv2_route (1 per route entry)
    - aws_lambda_permission (1 per connection)

Generated resources (authorizer role):
    - aws_apigatewayv2_authorizer
    - aws_lambda_permission
"""

import logging
import re

from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler

logger = logging.getLogger(__name__)


def _sanitize_path(path: str) -> str:
    """Sanitize a route path for use in Terraform resource names.

    Replaces ``/``, ``{``, and ``}`` with underscores, collapses consecutive
    underscores into one, and strips leading/trailing underscores.
    """
    result = re.sub(r"[/{}]", "_", path)
    result = re.sub(r"_+", "_", result)
    return result.strip("_")


class ApiGatewayLambdaHandler(BaseConnectionHandler):
    """Handles API Gateway → Lambda connections (route_handler and authorizer roles)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Dispatch based on connection_role in connection_config."""
        role = connection.connection_config.get("connection_role", "route_handler")

        if role == "authorizer":
            return self._handle_authorizer(connection, project)
        return self._handle_route_handler(connection, project)

    def _handle_route_handler(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Generate integration, route(s), and permission.

        Uses the ``routes`` array from connection_config. Each entry must have
        ``method`` and ``path`` keys. Generates one integration shared across all
        routes, one route resource per entry, and one Lambda permission.
        """
        source = connection.source_name
        target = connection.target_name
        category = get_category(ServiceType.API_GATEWAY)
        integration_name = f"{source}_{target}_integration"

        # Read integration settings from connection_config
        integration_type = connection.connection_config.get(
            "integration_type", "AWS_PROXY"
        )
        payload_format_version = connection.connection_config.get(
            "payload_format_version", "2.0"
        )
        vpc_link_name = connection.connection_config.get("vpc_link_name")

        # --- Integration ---
        integration_attrs: dict[str, str] = {
            "api_id": f"aws_apigatewayv2_api.{source}.id",
            "integration_type": integration_type,
            "integration_uri": f"aws_lambda_function.{target}.invoke_arn",
            "payload_format_version": payload_format_version,
        }

        if vpc_link_name:
            integration_attrs["connection_type"] = "VPC_LINK"
            integration_attrs["connection_id"] = (
                f"aws_apigatewayv2_vpc_link.{vpc_link_name}.id"
            )

        integration_content = self._renderer.render_resource(
            "aws_apigatewayv2_integration", integration_name, integration_attrs
        )
        integration_path = (
            f"{project.project_name}/modules/{category}/api-gateway/{source}/"
            f"integration_{target}.tf"
        )

        # --- Route(s) via routes array ---
        routes: list[dict[str, str]] = connection.connection_config.get("routes", [])

        route_files: list[GeneratedFile] = []
        for route in routes:
            method = route["method"]
            path = route["path"]
            route_key = f"{method} {path}"
            sanitized = _sanitize_path(path)
            route_name = f"{source}_{target}_route_{method.lower()}_{sanitized}"
            route_file_name = f"route_{target}_{method.lower()}_{sanitized}.tf"

            route_attrs = {
                "api_id": f"aws_apigatewayv2_api.{source}.id",
                "route_key": route_key,
                "target": (
                    f"integrations/${{aws_apigatewayv2_integration.{integration_name}.id}}"
                ),
            }
            route_content = self._renderer.render_resource(
                "aws_apigatewayv2_route", route_name, route_attrs
            )
            route_file_path = (
                f"{project.project_name}/modules/{category}/api-gateway/{source}/"
                f"{route_file_name}"
            )
            route_files.append(
                GeneratedFile(path=route_file_path, content=route_content)
            )

        # --- Lambda Permission ---
        permission_name = f"{source}_{target}_permission"
        permission_attrs = {
            "statement_id": f"AllowAPIGatewayInvoke_{source}_{target}",
            "action": "lambda:InvokeFunction",
            "function_name": f"aws_lambda_function.{target}.function_name",
            "principal": "apigateway.amazonaws.com",
            "source_arn": f"${{aws_apigatewayv2_api.{source}.execution_arn}}/*/*",
        }
        permission_content = self._renderer.render_resource(
            "aws_lambda_permission", permission_name, permission_attrs
        )
        permission_file_path = (
            f"{project.project_name}/modules/{category}/api-gateway/{source}/"
            f"permission_{target}.tf"
        )

        return [
            GeneratedFile(path=integration_path, content=integration_content),
            *route_files,
            GeneratedFile(path=permission_file_path, content=permission_content),
        ]

    def _handle_authorizer(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Generate authorizer and permission resources.

        Generates an ``aws_apigatewayv2_authorizer`` with type "REQUEST" and an
        ``aws_lambda_permission`` for authorizer invocation.
        Does NOT generate integration or route resources.
        """
        source = connection.source_name
        target = connection.target_name
        category = get_category(ServiceType.API_GATEWAY)
        authorizer_name = f"{source}_{target}_authorizer"
        permission_name = f"{source}_{target}_authorizer_permission"

        authorizer_display_name = connection.connection_config.get(
            "authorizer_name", target
        )
        payload_format_version = connection.connection_config.get(
            "payload_format_version", "2.0"
        )

        # --- Authorizer ---
        authorizer_attrs = {
            "api_id": f"aws_apigatewayv2_api.{source}.id",
            "name": authorizer_display_name,
            "authorizer_type": "REQUEST",
            "authorizer_uri": f"aws_lambda_function.{target}.invoke_arn",
            "authorizer_payload_format_version": payload_format_version,
        }
        authorizer_content = self._renderer.render_resource(
            "aws_apigatewayv2_authorizer", authorizer_name, authorizer_attrs
        )
        authorizer_path = (
            f"{project.project_name}/modules/{category}/api-gateway/{source}/"
            f"authorizer_{target}.tf"
        )

        # --- Lambda Permission for authorizer ---
        permission_attrs = {
            "statement_id": f"AllowAPIGatewayAuthorizer_{source}_{target}",
            "action": "lambda:InvokeFunction",
            "function_name": f"aws_lambda_function.{target}.function_name",
            "principal": "apigateway.amazonaws.com",
            "source_arn": (
                f"${{aws_apigatewayv2_api.{source}.execution_arn}}/authorizers/*"
            ),
        }
        permission_content = self._renderer.render_resource(
            "aws_lambda_permission", permission_name, permission_attrs
        )
        permission_path = (
            f"{project.project_name}/modules/{category}/api-gateway/{source}/"
            f"authorizer_permission_{target}.tf"
        )

        return [
            GeneratedFile(path=authorizer_path, content=authorizer_content),
            GeneratedFile(path=permission_path, content=permission_content),
        ]
