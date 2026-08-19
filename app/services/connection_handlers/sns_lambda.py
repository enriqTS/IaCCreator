"""SNS → Lambda connection handler — the Lambda module owns the subscription."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class SNSLambdaHandler(BaseConnectionHandler):
    """Handles SNS → Lambda connections (topic subscription plus invoke permission)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        topic = connection.source_name
        function = connection.target_name
        topic_arn_var = f"{safe_identifier(topic)}_topic_arn"

        subscription = self._renderer.render_resource(
            "aws_sns_topic_subscription",
            f"{safe_identifier(topic)}_subscription",
            {
                "topic_arn": Expr(f"var.{topic_arn_var}"),
                "protocol": "lambda",
                "endpoint": Expr(f"aws_lambda_function.{function}.arn"),
            },
        )
        permission = self._renderer.render_resource(
            "aws_lambda_permission",
            f"{safe_identifier(topic)}_permission",
            {
                "statement_id": f"AllowSNSInvoke{safe_identifier(topic)}",
                "action": "lambda:InvokeFunction",
                "function_name": Expr(f"aws_lambda_function.{function}.function_name"),
                "principal": "sns.amazonaws.com",
                "source_arn": Expr(f"var.{topic_arn_var}"),
            },
        )

        return ConnectionContribution(
            outputs=[
                self._output(topic, "arn", f"aws_sns_topic.{topic}.arn", "Topic ARN")
            ],
            inputs=[
                self._input(
                    function,
                    topic,
                    "topic_arn",
                    f"module.{topic}.arn",
                    f"ARN of the {topic} topic this function subscribes to",
                )
            ],
            resources=[
                self._resource(function, f"subscription_{topic}.tf", subscription),
                self._resource(function, f"permission_{topic}.tf", permission),
            ],
        )
