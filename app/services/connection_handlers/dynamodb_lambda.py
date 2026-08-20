"""DynamoDB Streams → Lambda connection handler — the function consumes the stream."""

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.iam_registry import get_actions


class DynamoDBLambdaHandler(BaseConnectionHandler):
    """Wires a table's stream to a function through an event source mapping."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        table = connection.source_name
        function = connection.target_name
        stream_var = f"{safe_identifier(table)}_stream_arn"
        config = connection.connection_config

        attrs: dict[str, object] = {
            "event_source_arn": Expr(f"var.{stream_var}"),
            "function_name": Expr(f"aws_lambda_function.{function}.arn"),
            "starting_position": config.get("starting_position", "LATEST"),
            "batch_size": config.get("batch_size", 100),
        }
        mapping = self._renderer.render_resource(
            "aws_lambda_event_source_mapping",
            f"{safe_identifier(table)}_stream",
            attrs,
        )

        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.DYNAMODB, "stream"),
            resources=[Expr(f"${{aws_dynamodb_table.{table}.stream_arn}}")],
        )

        return ConnectionContribution(
            outputs=[
                self._output(
                    table,
                    "stream_arn",
                    f"aws_dynamodb_table.{table}.stream_arn",
                    "ARN of the table's stream",
                )
            ],
            inputs=[
                self._input(
                    function,
                    table,
                    "stream_arn",
                    f"module.{table}.stream_arn",
                    f"Stream ARN of the {table} table this function consumes",
                )
            ],
            resources=[self._resource(function, f"stream_{table}.tf", mapping)],
            iam=[self._grant(function, statement)],
        )
