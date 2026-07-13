"""SNS → Lambda connection handler.

Generates an ``aws_sns_topic_subscription`` (protocol "lambda") to subscribe
the Lambda function to the SNS topic, and an ``aws_lambda_permission`` allowing
SNS to invoke the Lambda.

Generated resources:
- aws_sns_topic_subscription
- aws_lambda_permission

IAM mutations:
- None (Lambda permission is resource-based, not identity-based).
"""

import logging

from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler

logger = logging.getLogger(__name__)


class SNSLambdaHandler(BaseConnectionHandler):
    """Handles SNS → Lambda connections (topic subscription + permission)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Generate SNS topic subscription and Lambda permission."""
        sns_name = connection.source_name
        lambda_name = connection.target_name

        category = get_category(ServiceType.SNS)

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
        subscription_path = f"{project.project_name}/modules/{category}/sns/{sns_name}/subscription_{lambda_name}.tf"

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
        permission_path = f"{project.project_name}/modules/{category}/sns/{sns_name}/permission_{lambda_name}.tf"

        return [
            GeneratedFile(path=subscription_path, content=subscription_content),
            GeneratedFile(path=permission_path, content=permission_content),
        ]
