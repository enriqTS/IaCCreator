"""ConnectionProcessor — processes resource connections and generates integration resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionIR,
    GeneratedFile,
    IAMStatement,
    ProjectIR,
    ResourceInstanceIR,
)


# IAM actions granted per target service type
_DYNAMODB_ACTIONS = [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
]

_S3_ACTIONS = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket",
]

_CLOUDWATCH_ACTIONS = [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
]


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
        """API Gateway → Lambda: generate ``aws_apigatewayv2_integration``."""
        source = connection.source_name
        target = connection.target_name
        integration_name = f"{source}_{target}_integration"

        attrs = {
            "api_id": f"aws_apigatewayv2_api.{source}.id",
            "integration_type": "AWS_PROXY",
            "integration_uri": f"aws_lambda_function.{target}.invoke_arn",
            "payload_format_version": "2.0",
        }
        content = self._renderer.render_resource(
            "aws_apigatewayv2_integration", integration_name, attrs
        )

        path = f"{project.project_name}/modules/api-gateway/{source}/integration_{target}.tf"
        return [GeneratedFile(path=path, content=content)]

    def _handle_lambda_dynamodb(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → DynamoDB: add read/write IAM statements to the Lambda instance."""
        target = connection.target_name
        statement = IAMStatement(
            effect="Allow",
            actions=_DYNAMODB_ACTIONS,
            resources=[f"${{aws_dynamodb_table.{target}.arn}}"],
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []

    def _handle_lambda_s3(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Lambda → S3: add S3 access IAM statements to the Lambda instance."""
        target = connection.target_name
        statement = IAMStatement(
            effect="Allow",
            actions=_S3_ACTIONS,
            resources=[
                f"${{aws_s3_bucket.{target}.arn}}",
                f"${{aws_s3_bucket.{target}.arn}}/*",
            ],
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
        statement = IAMStatement(
            effect="Allow",
            actions=_CLOUDWATCH_ACTIONS,
            resources=[f"arn:aws:logs:*:*:log-group:{log_group_name}:*"],
        )
        self._attach_iam_statement(source, statement, project)

        path = f"{project.project_name}/modules/cloudwatch/{target}/log_group_{source}.tf"
        return [GeneratedFile(path=path, content=content)]

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
}
