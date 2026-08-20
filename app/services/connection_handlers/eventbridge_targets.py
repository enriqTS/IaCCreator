"""EventBridge → target connections — the rule module owns every target it fires at."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


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

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        rule = connection.source_name
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
        # The queue policy lives here too, so values only ever flow queue → rule
        policy = self._renderer.render_resource(
            "aws_sqs_queue_policy",
            f"{prefix}_policy",
            {
                "queue_url": Expr(f"var.{prefix}_queue_url"),
                "policy": self._renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "events.amazonaws.com"},
                                "Action": "sqs:SendMessage",
                                "Resource": Expr(f"var.{prefix}_queue_arn"),
                                "Condition": {
                                    "ArnEquals": {
                                        "aws:SourceArn": Expr(
                                            f"aws_cloudwatch_event_rule.{rule}.arn"
                                        )
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
                self._resource(rule, f"policy_{queue}.tf", policy),
            ],
        )
