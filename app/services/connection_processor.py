"""ConnectionProcessor — processes resource connections and generates integration resources."""

import logging

from app.generators.hcl_renderer import HCLRenderer

logger = logging.getLogger(__name__)
from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionIR,
    GeneratedFile,
    IAMStatement,
    ProjectIR,
    ResourceInstanceIR,
)
from app.services.iam_registry import get_actions, get_resources


class ConnectionProcessor:
    """Processes connections between resources and produces integration HCL and IAM statements.

    For each connection type:
    - API Gateway → Lambda: generates an ``aws_apigatewayv2_integration`` resource
    - Lambda → DynamoDB: adds DynamoDB read/write IAM statements to the Lambda
    - Lambda → S3: adds S3 access IAM statements to the Lambda
    - Lambda → CloudWatch: generates an ``aws_cloudwatch_log_group`` resource

    All generated HCL uses Terraform resource references instead of hardcoded values.
    """

    def __init__(self) -> None:
        self._renderer = HCLRenderer()

    def process(self, connection: ConnectionIR, project: ProjectIR) -> list[GeneratedFile]:
        """Process a single connection and return any generated files.

        IAM statements are attached directly to the source Lambda's
        ``ResourceInstanceIR.iam_statements`` list (mutated in place).
        """
        pair = (connection.source_service, connection.target_service)
        handler = _CONNECTION_HANDLERS.get(pair)
        if handler is None:
            return []
        return handler(self, connection, project)

    def process_all(self, project: ProjectIR) -> list[GeneratedFile]:
        """Process every connection in the project and return all generated files."""
        files: list[GeneratedFile] = []
        for conn in project.connections:
            files.extend(self.process(conn, project))
        return files

    # ------------------------------------------------------------------
    # Connection handlers
    # ------------------------------------------------------------------

    def _handle_apigw_lambda(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """API Gateway → Lambda: dispatch based on connection_role.

        When role is "authorizer", generates authorizer + permission resources.
        When role is "route_handler" (default), generates integration, route, and permission.
        """
        role = connection.connection_config.get("connection_role", "route_handler")

        if role == "authorizer":
            return self._handle_apigw_lambda_authorizer(connection, project)
        return self._handle_apigw_lambda_route_handler(connection, project)

    def _handle_apigw_lambda_route_handler(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """API Gateway → Lambda (route_handler): generate integration, route(s), and permission.

        Supports enhanced integration configuration via connection_config:
        - integration_type: defaults to "AWS_PROXY"
        - payload_format_version: defaults to "2.0"
        - vpc_link_name: when present, adds connection_type="VPC_LINK" and connection_id

        When http_method contains comma-separated values (e.g., "GET,POST"), generates
        one route resource per method sharing the same integration.
        """
        source = connection.source_name
        target = connection.target_name
        integration_name = f"{source}_{target}_integration"

        # Read enhanced integration settings from connection_config (with backward-compatible defaults)
        integration_type = connection.connection_config.get("integration_type", "AWS_PROXY")
        payload_format_version = connection.connection_config.get("payload_format_version", "2.0")
        vpc_link_name = connection.connection_config.get("vpc_link_name")

        # --- Integration ---
        integration_attrs = {
            "api_id": f"aws_apigatewayv2_api.{source}.id",
            "integration_type": integration_type,
            "integration_uri": f"aws_lambda_function.{target}.invoke_arn",
            "payload_format_version": payload_format_version,
        }

        # Add VPC link attributes when vpc_link_name is specified
        if vpc_link_name:
            integration_attrs["connection_type"] = "VPC_LINK"
            integration_attrs["connection_id"] = (
                f"aws_apigatewayv2_vpc_link.{vpc_link_name}.id"
            )

        integration_content = self._renderer.render_resource(
            "aws_apigatewayv2_integration", integration_name, integration_attrs
        )
        integration_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.API_GATEWAY)}/api-gateway/{source}/integration_{target}.tf"
        )

        # --- Route(s) ---
        route_path = connection.connection_config.get("route_path", "/$default")
        http_method = connection.connection_config.get("http_method", "ANY")

        # Split comma-separated methods and generate one route per method
        methods = [m.strip() for m in str(http_method).split(",") if m.strip()]
        if not methods:
            methods = ["ANY"]

        route_files: list[GeneratedFile] = []
        for method in methods:
            route_key = f"{method} {route_path}"
            # Use method suffix in resource name only when multiple methods exist
            if len(methods) == 1:
                route_name = f"{source}_{target}_route"
                route_file_name = f"route_{target}.tf"
            else:
                route_name = f"{source}_{target}_route_{method.lower()}"
                route_file_name = f"route_{target}_{method.lower()}.tf"

            route_attrs = {
                "api_id": f"aws_apigatewayv2_api.{source}.id",
                "route_key": route_key,
                "target": f"integrations/${{aws_apigatewayv2_integration.{integration_name}.id}}",
            }
            route_content = self._renderer.render_resource(
                "aws_apigatewayv2_route", route_name, route_attrs
            )
            route_file_path = (
                f"{project.project_name}/modules/{get_category(ServiceType.API_GATEWAY)}/api-gateway/{source}/{route_file_name}"
            )
            route_files.append(GeneratedFile(path=route_file_path, content=route_content))

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
            f"{project.project_name}/modules/{get_category(ServiceType.API_GATEWAY)}/api-gateway/{source}/permission_{target}.tf"
        )

        return [
            GeneratedFile(path=integration_path, content=integration_content),
            *route_files,
            GeneratedFile(path=permission_file_path, content=permission_content),
        ]

    def _handle_apigw_lambda_authorizer(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """API Gateway → Lambda (authorizer): generate authorizer and permission resources.

        Generates:
        - aws_apigatewayv2_authorizer with type "REQUEST"
        - aws_lambda_permission for authorizer invocation

        Does NOT generate integration or route resources.
        """
        source = connection.source_name
        target = connection.target_name
        authorizer_name = f"{source}_{target}_authorizer"
        permission_name = f"{source}_{target}_authorizer_permission"

        # Read authorizer settings from connection_config
        authorizer_display_name = connection.connection_config.get("authorizer_name", target)
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
            f"{project.project_name}/modules/{get_category(ServiceType.API_GATEWAY)}/api-gateway/{source}/authorizer_{target}.tf"
        )

        # --- Lambda Permission for authorizer ---
        permission_attrs = {
            "statement_id": f"AllowAPIGatewayAuthorizer_{source}_{target}",
            "action": "lambda:InvokeFunction",
            "function_name": f"aws_lambda_function.{target}.function_name",
            "principal": "apigateway.amazonaws.com",
            "source_arn": f"${{aws_apigatewayv2_api.{source}.execution_arn}}/authorizers/*",
        }
        permission_content = self._renderer.render_resource(
            "aws_lambda_permission", permission_name, permission_attrs
        )
        permission_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.API_GATEWAY)}/api-gateway/{source}/authorizer_permission_{target}.tf"
        )

        return [
            GeneratedFile(path=authorizer_path, content=authorizer_content),
            GeneratedFile(path=permission_path, content=permission_content),
        ]

    def _handle_lambda_dynamodb(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → DynamoDB: add IAM statements based on access_pattern config."""
        target = connection.target_name
        access_pattern = connection.connection_config.get("access_pattern", "full")

        actions = get_actions(ServiceType.DYNAMODB, access_pattern)

        statement = IAMStatement(
            effect="Allow",
            actions=actions,
            resources=get_resources(target, ServiceType.DYNAMODB),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []

    def _handle_lambda_s3(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → S3: add IAM statements based on access_pattern config."""
        target = connection.target_name
        access_pattern = connection.connection_config.get("access_pattern", "full")

        actions = get_actions(ServiceType.S3, access_pattern)

        statement = IAMStatement(
            effect="Allow",
            actions=actions,
            resources=get_resources(target, ServiceType.S3),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []

    def _handle_lambda_cloudwatch(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → CloudWatch: generate a ``aws_cloudwatch_log_group`` resource."""
        source = connection.source_name
        target = connection.target_name
        log_group_name = f"/aws/lambda/{source}"

        attrs = {
            "name": log_group_name,
        }
        content = self._renderer.render_resource(
            "aws_cloudwatch_log_group", f"{source}_log_group", attrs
        )

        # Also add CloudWatch Logs IAM statements to the Lambda
        # Keep custom resource reference here — uses source-based log group path, not standard target pattern
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.CLOUDWATCH, "full"),
            resources=[f"arn:aws:logs:*:*:log-group:{log_group_name}:*"],
        )
        self._attach_iam_statement(source, statement, project)

        path = f"{project.project_name}/modules/{get_category(ServiceType.CLOUDWATCH)}/cloudwatch/{target}/log_group_{source}.tf"
        return [GeneratedFile(path=path, content=content)]

    # ------------------------------------------------------------------
    # Lambda → SNS
    # ------------------------------------------------------------------

    def _handle_lambda_sns(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → SNS: add sns:Publish IAM statement to the Lambda instance."""
        target = connection.target_name
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.SNS, "full"),
            resources=get_resources(target, ServiceType.SNS),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []

    # ------------------------------------------------------------------
    # Lambda → SQS
    # ------------------------------------------------------------------

    def _handle_lambda_sqs(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → SQS: add sqs:SendMessage IAM statement to the Lambda instance."""
        target = connection.target_name
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.SQS, "write"),
            resources=get_resources(target, ServiceType.SQS),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []

    # ------------------------------------------------------------------
    # SQS → Lambda
    # ------------------------------------------------------------------

    def _handle_sqs_lambda(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """SQS → Lambda: generate event source mapping, permission, and IAM statements."""
        sqs_name = connection.source_name
        lambda_name = connection.target_name

        # --- Event Source Mapping ---
        mapping_name = f"{sqs_name}_{lambda_name}_event_source"
        mapping_attrs: dict[str, str | int] = {
            "event_source_arn": f"aws_sqs_queue.{sqs_name}.arn",
            "function_name": f"aws_lambda_function.{lambda_name}.arn",
            "batch_size": connection.connection_config.get("batch_size", 10),
        }
        batching_window = connection.connection_config.get("maximum_batching_window_in_seconds")
        if batching_window is not None:
            mapping_attrs["maximum_batching_window_in_seconds"] = batching_window

        mapping_content = self._renderer.render_resource(
            "aws_lambda_event_source_mapping", mapping_name, mapping_attrs
        )
        mapping_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.SQS)}/sqs/{sqs_name}/event_source_{lambda_name}.tf"
        )

        # --- Lambda Permission ---
        permission_name = f"{sqs_name}_{lambda_name}_permission"
        permission_attrs = {
            "statement_id": f"AllowSQSInvoke_{sqs_name}_{lambda_name}",
            "action": "lambda:InvokeFunction",
            "function_name": f"aws_lambda_function.{lambda_name}.function_name",
            "principal": "sqs.amazonaws.com",
            "source_arn": f"${{aws_sqs_queue.{sqs_name}.arn}}",
        }
        permission_content = self._renderer.render_resource(
            "aws_lambda_permission", permission_name, permission_attrs
        )
        permission_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.SQS)}/sqs/{sqs_name}/permission_{lambda_name}.tf"
        )

        # --- IAM statements for the Lambda to receive from SQS ---
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.SQS, "read"),
            resources=get_resources(sqs_name, ServiceType.SQS),
        )
        self._attach_iam_statement(lambda_name, statement, project)

        return [
            GeneratedFile(path=mapping_path, content=mapping_content),
            GeneratedFile(path=permission_path, content=permission_content),
        ]

    # ------------------------------------------------------------------
    # SNS → SQS
    # ------------------------------------------------------------------

    def _handle_sns_sqs(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """SNS → SQS: generate topic subscription and queue policy."""
        sns_name = connection.source_name
        sqs_name = connection.target_name

        # --- SNS Topic Subscription ---
        subscription_name = f"{sns_name}_{sqs_name}_subscription"
        subscription_attrs = {
            "topic_arn": f"aws_sns_topic.{sns_name}.arn",
            "protocol": "sqs",
            "endpoint": f"aws_sqs_queue.{sqs_name}.arn",
        }
        subscription_content = self._renderer.render_resource(
            "aws_sns_topic_subscription", subscription_name, subscription_attrs
        )
        subscription_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.SNS)}/sns/{sns_name}/subscription_{sqs_name}.tf"
        )

        # --- SQS Queue Policy ---
        policy_name = f"{sqs_name}_{sns_name}_policy"
        policy_attrs = {
            "queue_url": f"aws_sqs_queue.{sqs_name}.url",
            "policy": (
                'jsonencode({\n'
                '    Version = "2012-10-17"\n'
                '    Statement = [\n'
                '      {\n'
                '        Effect   = "Allow"\n'
                '        Principal = {\n'
                '          Service = "sns.amazonaws.com"\n'
                '        }\n'
                '        Action   = "SQS:SendMessage"\n'
                f'        Resource = aws_sqs_queue.{sqs_name}.arn\n'
                '        Condition = {{\n'
                '          ArnEquals = {{\n'
                f'            "aws:SourceArn" = aws_sns_topic.{sns_name}.arn\n'
                '          }}\n'
                '        }}\n'
                '      }\n'
                '    ]\n'
                '  })'
            ),
        }
        policy_content = self._renderer.render_resource(
            "aws_sqs_queue_policy", policy_name, policy_attrs
        )
        policy_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.SQS)}/sqs/{sqs_name}/policy_{sns_name}.tf"
        )

        return [
            GeneratedFile(path=subscription_path, content=subscription_content),
            GeneratedFile(path=policy_path, content=policy_content),
        ]

    # ------------------------------------------------------------------
    # SNS → Lambda
    # ------------------------------------------------------------------

    def _handle_sns_lambda(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """SNS → Lambda: generate topic subscription and Lambda permission."""
        sns_name = connection.source_name
        lambda_name = connection.target_name

        # --- SNS Topic Subscription ---
        subscription_name = f"{sns_name}_{lambda_name}_subscription"
        subscription_attrs = {
            "topic_arn": f"aws_sns_topic.{sns_name}.arn",
            "protocol": "lambda",
            "endpoint": f"aws_lambda_function.{lambda_name}.arn",
        }
        subscription_content = self._renderer.render_resource(
            "aws_sns_topic_subscription", subscription_name, subscription_attrs
        )
        subscription_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.SNS)}/sns/{sns_name}/subscription_{lambda_name}.tf"
        )

        # --- Lambda Permission ---
        permission_name = f"{sns_name}_{lambda_name}_permission"
        permission_attrs = {
            "statement_id": f"AllowSNSInvoke_{sns_name}_{lambda_name}",
            "action": "lambda:InvokeFunction",
            "function_name": f"aws_lambda_function.{lambda_name}.function_name",
            "principal": "sns.amazonaws.com",
            "source_arn": f"${{aws_sns_topic.{sns_name}.arn}}",
        }
        permission_content = self._renderer.render_resource(
            "aws_lambda_permission", permission_name, permission_attrs
        )
        permission_path = (
            f"{project.project_name}/modules/{get_category(ServiceType.SNS)}/sns/{sns_name}/permission_{lambda_name}.tf"
        )

        return [
            GeneratedFile(path=subscription_path, content=subscription_content),
            GeneratedFile(path=permission_path, content=permission_content),
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _attach_iam_statement(
        self, lambda_name: str, statement: IAMStatement, project: ProjectIR
    ) -> None:
        """Find the Lambda ResourceInstanceIR in the project and append the IAM statement."""
        instance = self._find_instance(lambda_name, project)
        if instance is not None:
            instance.iam_statements.append(statement)

    @staticmethod
    def _find_instance(name: str, project: ProjectIR) -> ResourceInstanceIR | None:
        """Look up a resource instance by name across all modules."""
        for module in project.modules:
            for inst in module.instances:
                if inst.name == name:
                    return inst
        return None


# Dispatch table mapping (source_service, target_service) → handler method
_CONNECTION_HANDLERS: dict[
    tuple[ServiceType, ServiceType],
    "callable",
] = {
    (ServiceType.API_GATEWAY, ServiceType.LAMBDA): ConnectionProcessor._handle_apigw_lambda,
    (ServiceType.LAMBDA, ServiceType.DYNAMODB): ConnectionProcessor._handle_lambda_dynamodb,
    (ServiceType.LAMBDA, ServiceType.S3): ConnectionProcessor._handle_lambda_s3,
    (ServiceType.LAMBDA, ServiceType.CLOUDWATCH): ConnectionProcessor._handle_lambda_cloudwatch,
    (ServiceType.LAMBDA, ServiceType.SNS): ConnectionProcessor._handle_lambda_sns,
    (ServiceType.LAMBDA, ServiceType.SQS): ConnectionProcessor._handle_lambda_sqs,
    (ServiceType.SQS, ServiceType.LAMBDA): ConnectionProcessor._handle_sqs_lambda,
    (ServiceType.SNS, ServiceType.SQS): ConnectionProcessor._handle_sns_sqs,
    (ServiceType.SNS, ServiceType.LAMBDA): ConnectionProcessor._handle_sns_lambda,
}
