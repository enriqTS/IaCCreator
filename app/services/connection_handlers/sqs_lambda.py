"""SQS → Lambda connection handler — the Lambda module owns the event source mapping."""

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.iam_registry import get_actions, get_resources


class SQSLambdaHandler(BaseConnectionHandler):
    """Handles SQS → Lambda connections (event source mapping, permission, IAM)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        queue = connection.source_name
        function = connection.target_name
        queue_arn_var = f"{safe_identifier(queue)}_queue_arn"

        mapping_attrs: dict[str, object] = {
            "event_source_arn": Expr(f"var.{queue_arn_var}"),
            "function_name": Expr(f"aws_lambda_function.{function}.arn"),
            "batch_size": connection.connection_config.get("batch_size", 10),
        }
        window = connection.connection_config.get("maximum_batching_window_in_seconds")
        if window is not None:
            mapping_attrs["maximum_batching_window_in_seconds"] = window

        mapping = self._renderer.render_resource(
            "aws_lambda_event_source_mapping",
            f"{safe_identifier(queue)}_event_source",
            mapping_attrs,
        )
        permission = self._renderer.render_resource(
            "aws_lambda_permission",
            f"{safe_identifier(queue)}_permission",
            {
                "statement_id": f"AllowSQSInvoke{safe_identifier(queue)}",
                "action": "lambda:InvokeFunction",
                "function_name": Expr(f"aws_lambda_function.{function}.function_name"),
                "principal": "sqs.amazonaws.com",
                "source_arn": Expr(f"var.{queue_arn_var}"),
            },
        )

        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.SQS, "read"),
            resources=get_resources(queue, ServiceType.SQS),
        )

        return ConnectionContribution(
            outputs=[
                self._output(queue, "arn", f"aws_sqs_queue.{queue}.arn", "Queue ARN")
            ],
            inputs=[
                self._input(
                    function,
                    queue,
                    "queue_arn",
                    f"module.{queue}.arn",
                    f"ARN of the {queue} queue this function consumes",
                )
            ],
            resources=[
                self._resource(function, f"event_source_{queue}.tf", mapping),
                self._resource(function, f"permission_{queue}.tf", permission),
            ],
            iam=[self._grant(function, statement)],
        )
