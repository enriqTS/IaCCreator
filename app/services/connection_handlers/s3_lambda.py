"""S3 → Lambda connection handler — the bucket module owns the notification."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class S3LambdaHandler(BaseConnectionHandler):
    """Notifies a Lambda when objects change in a bucket."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bucket = connection.source_name
        function = connection.target_name
        prefix = safe_identifier(function)
        config = connection.connection_config

        lambda_block: dict[str, object] = {
            "lambda_function_arn": Expr(f"var.{prefix}_function_arn"),
            "events": config.get("events") or ["s3:ObjectCreated:*"],
        }
        if config.get("filter_prefix"):
            lambda_block["filter_prefix"] = config["filter_prefix"]
        if config.get("filter_suffix"):
            lambda_block["filter_suffix"] = config["filter_suffix"]

        notification = self._renderer.render_resource(
            "aws_s3_bucket_notification",
            f"{safe_identifier(bucket)}_notification",
            {
                "bucket": Expr(f"aws_s3_bucket.{bucket}.id"),
                "lambda_function": lambda_block,
                "depends_on": Expr(f"[aws_lambda_permission.{prefix}_permission]"),
            },
        )
        permission = self._renderer.render_resource(
            "aws_lambda_permission",
            f"{prefix}_permission",
            {
                "statement_id": f"AllowS3Invoke{prefix}",
                "action": "lambda:InvokeFunction",
                "function_name": Expr(f"var.{prefix}_function_name"),
                "principal": "s3.amazonaws.com",
                "source_arn": Expr(f"aws_s3_bucket.{bucket}.arn"),
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
                    bucket,
                    function,
                    "function_arn",
                    f"module.{function}.function_arn",
                    f"ARN of the {function} function this bucket notifies",
                ),
                self._input(
                    bucket,
                    function,
                    "function_name",
                    f"module.{function}.function_name",
                    f"Name of the {function} function this bucket notifies",
                ),
            ],
            resources=[
                self._resource(bucket, f"notification_{function}.tf", notification),
                self._resource(bucket, f"permission_{function}.tf", permission),
            ],
        )
