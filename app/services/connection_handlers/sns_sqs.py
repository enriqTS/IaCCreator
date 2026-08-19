"""SNS → SQS connection handler — the queue module owns the subscription and policy."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class SNSSQSHandler(BaseConnectionHandler):
    """Handles SNS → SQS connections (topic subscription plus queue policy)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
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
            },
        )
        policy = self._renderer.render_resource(
            "aws_sqs_queue_policy",
            f"{safe_identifier(topic)}_policy",
            {
                "queue_url": Expr(f"aws_sqs_queue.{queue}.url"),
                "policy": self._renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "sns.amazonaws.com"},
                                "Action": "SQS:SendMessage",
                                "Resource": Expr(f"aws_sqs_queue.{queue}.arn"),
                                "Condition": {
                                    "ArnEquals": {
                                        "aws:SourceArn": Expr(f"var.{topic_arn_var}")
                                    }
                                },
                            }
                        ],
                    },
                    depth=2,
                ),
            },
        )

        return ConnectionContribution(
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
                self._resource(queue, f"policy_{topic}.tf", policy),
            ],
        )
