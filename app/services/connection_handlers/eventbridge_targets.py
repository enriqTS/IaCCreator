"""EventBridge → target connections — the rule module owns every target it fires at."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
    require_custom_delivery_key,
)
from app.services.connection_handlers.queue_delivery_policy import QueueDeliveryPolicy


class EventBridgeLambdaHandler(BaseConnectionHandler):
    """Fires a rule at a Lambda, and lets EventBridge invoke it."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        rule = connection.source_name
        function = connection.target_name
        prefix = safe_identifier(function)

        target_attrs: dict[str, object] = {
            "rule": Expr(f"aws_cloudwatch_event_rule.{rule}.name"),
            "target_id": connection.connection_config.get("target_id") or prefix,
            "arn": Expr(f"var.{prefix}_function_arn"),
        }
        if connection.connection_config.get("input"):
            target_attrs["input"] = connection.connection_config["input"]

        target = self._renderer.render_resource(
            "aws_cloudwatch_event_target", f"{prefix}_target", target_attrs
        )
        permission = self._renderer.render_resource(
            "aws_lambda_permission",
            f"{prefix}_permission",
            {
                "statement_id": f"AllowEventBridgeInvoke{prefix}",
                "action": "lambda:InvokeFunction",
                "function_name": Expr(f"var.{prefix}_function_name"),
                "principal": "events.amazonaws.com",
                "source_arn": Expr(f"aws_cloudwatch_event_rule.{rule}.arn"),
            },
        )

        return ConnectionContribution(
            outputs=[
                self._output(
                    function,
                    "function_arn",
                    f"aws_lambda_function.{function}.arn",
                    "ARN of the Lambda function",
                ),
                self._output(
                    function,
                    "function_name",
                    f"aws_lambda_function.{function}.function_name",
                    "Name of the Lambda function",
                ),
            ],
            inputs=[
                self._input(
                    rule,
                    function,
                    "function_arn",
                    f"module.{function}.function_arn",
                    f"ARN of the {function} function this rule invokes",
                ),
                self._input(
                    rule,
                    function,
                    "function_name",
                    f"module.{function}.function_name",
                    f"Name of the {function} function this rule invokes",
                ),
            ],
            resources=[
                self._resource(rule, f"target_{function}.tf", target),
                self._resource(rule, f"permission_{function}.tf", permission),
            ],
        )


class EventBridgeSQSHandler(BaseConnectionHandler):
    """Fires a rule at an SQS queue, and lets EventBridge send to it."""

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return external_service_key_issues(connection, project)

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        rule = connection.source_name
        require_custom_delivery_key(connection, project)
        queue = connection.target_name
        prefix = safe_identifier(queue)

        target = self._renderer.render_resource(
            "aws_cloudwatch_event_target",
            f"{prefix}_target",
            {
                "rule": Expr(f"aws_cloudwatch_event_rule.{rule}.name"),
                "target_id": connection.connection_config.get("target_id") or prefix,
                "arn": Expr(f"var.{prefix}_queue_arn"),
            },
        )
        result = ConnectionContribution(
            outputs=[
                self._output(queue, "arn", f"aws_sqs_queue.{queue}.arn", "Queue ARN"),
                self._output(queue, "url", f"aws_sqs_queue.{queue}.url", "Queue URL"),
            ],
            inputs=[
                self._input(
                    rule,
                    queue,
                    "queue_arn",
                    f"module.{queue}.arn",
                    f"ARN of the {queue} queue this rule targets",
                ),
                self._input(
                    rule,
                    queue,
                    "queue_url",
                    f"module.{queue}.url",
                    f"URL of the {queue} queue this rule targets",
                ),
            ],
            resources=[
                self._resource(rule, f"target_{queue}.tf", target),
            ],
        )
        result.merge(QueueDeliveryPolicy().handle(connection, project))
        return result
