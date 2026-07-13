"""Lambda → CloudWatch connection handler.

Generates an ``aws_cloudwatch_log_group`` resource for the Lambda function and
attaches CloudWatch Logs IAM statements (CreateLogGroup, CreateLogStream, PutLogEvents)
to the source Lambda instance.

Generated resources:
- aws_cloudwatch_log_group

IAM mutations:
- Appends CloudWatch Logs write statements to the source Lambda.
"""

import logging

from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, IAMStatement, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions

logger = logging.getLogger(__name__)


class LambdaCloudWatchHandler(BaseConnectionHandler):
    """Handles Lambda → CloudWatch connections (log group HCL + IAM)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Generate a CloudWatch log group and attach Logs IAM to the Lambda."""
        source = connection.source_name
        target = connection.target_name
        log_group_name = f"/aws/lambda/{source}"

        attrs = {
            "name": log_group_name,
        }
        content = self._renderer.render_resource(
            "aws_cloudwatch_log_group", f"{source}_log_group", attrs
        )

        # Attach CloudWatch Logs IAM statements to the Lambda
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.CLOUDWATCH, "full"),
            resources=[f"arn:aws:logs:*:*:log-group:{log_group_name}:*"],
        )
        self._attach_iam_statement(source, statement, project)

        category = get_category(ServiceType.CLOUDWATCH)
        path = f"{project.project_name}/modules/{category}/cloudwatch/{target}/log_group_{source}.tf"
        return [GeneratedFile(path=path, content=content)]
