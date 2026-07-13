"""SNS → SQS connection handler.

Generates an ``aws_sns_topic_subscription`` (protocol "sqs") to subscribe the
SQS queue to the SNS topic, and an ``aws_sqs_queue_policy`` allowing the SNS
topic to send messages to the queue.

Generated resources:
- aws_sns_topic_subscription
- aws_sqs_queue_policy

IAM mutations:
- None (queue policy is resource-based, not identity-based).
"""

import logging

from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler

logger = logging.getLogger(__name__)


class SNSSQSHandler(BaseConnectionHandler):
    """Handles SNS → SQS connections (topic subscription + queue policy)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Generate SNS topic subscription and SQS queue policy."""
        sns_name = connection.source_name
        sqs_name = connection.target_name

        sns_category = get_category(ServiceType.SNS)
        sqs_category = get_category(ServiceType.SQS)

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
        subscription_path = f"{project.project_name}/modules/{sns_category}/sns/{sns_name}/subscription_{sqs_name}.tf"

        # --- SQS Queue Policy ---
        policy_name = f"{sqs_name}_{sns_name}_policy"
        policy_attrs = {
            "queue_url": f"aws_sqs_queue.{sqs_name}.url",
            "policy": (
                "jsonencode({\n"
                '    Version = "2012-10-17"\n'
                "    Statement = [\n"
                "      {\n"
                '        Effect   = "Allow"\n'
                "        Principal = {\n"
                '          Service = "sns.amazonaws.com"\n'
                "        }\n"
                '        Action   = "SQS:SendMessage"\n'
                f"        Resource = aws_sqs_queue.{sqs_name}.arn\n"
                "        Condition = {{\n"
                "          ArnEquals = {{\n"
                f'            "aws:SourceArn" = aws_sns_topic.{sns_name}.arn\n'
                "          }}\n"
                "        }}\n"
                "      }\n"
                "    ]\n"
                "  })"
            ),
        }
        policy_content = self._renderer.render_resource(
            "aws_sqs_queue_policy", policy_name, policy_attrs
        )
        policy_path = f"{project.project_name}/modules/{sqs_category}/sqs/{sqs_name}/policy_{sns_name}.tf"

        return [
            GeneratedFile(path=subscription_path, content=subscription_content),
            GeneratedFile(path=policy_path, content=policy_content),
        ]
