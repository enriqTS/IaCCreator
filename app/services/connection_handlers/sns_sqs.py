"""SNS → SQS connection handler — the queue module owns the subscription and policy."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
    require_custom_delivery_key,
)
from app.services.connection_handlers.queue_delivery_policy import QueueDeliveryPolicy


class SNSSQSHandler(BaseConnectionHandler):
    """Handles SNS → SQS connections (topic subscription plus queue policy)."""

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return external_service_key_issues(connection, project)

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        require_custom_delivery_key(connection, project)
        topic = connection.source_name
        queue = connection.target_name
        topic_arn_var = f"{safe_identifier(topic)}_topic_arn"

        subscription = self._renderer.render_resource(
            "aws_sns_topic_subscription",
            f"{safe_identifier(topic)}_subscription",
            {
                "topic_arn": Expr(f"var.{topic_arn_var}"),
                "protocol": "sqs",
                "endpoint": Expr(f"aws_sqs_queue.{queue}.arn"),
                "depends_on": Expr("[aws_sqs_queue_policy.delivery]"),
            },
        )
        result = ConnectionContribution(
            outputs=[
                self._output(topic, "arn", f"aws_sns_topic.{topic}.arn", "Topic ARN")
            ],
            inputs=[
                self._input(
                    queue,
                    topic,
                    "topic_arn",
                    f"module.{topic}.arn",
                    f"ARN of the {topic} topic that publishes to this queue",
                )
            ],
            resources=[
                self._resource(queue, f"subscription_{topic}.tf", subscription),
            ],
        )
        result.merge(QueueDeliveryPolicy().handle(connection, project))
        return result
