"""SQS → Lambda connection handler.

Generates an ``aws_lambda_event_source_mapping`` resource to wire the SQS queue
as an event source for the Lambda, an ``aws_lambda_permission`` to allow SQS to
invoke the Lambda, and attaches SQS read IAM statements to the Lambda instance.

Supports ``batch_size`` and ``maximum_batching_window_in_seconds`` via connection_config.

Generated resources:
- aws_lambda_event_source_mapping
- aws_lambda_permission

IAM mutations:
- Appends SQS read statements (ReceiveMessage, DeleteMessage, GetQueueAttributes)
  to the target Lambda.
"""

import logging

from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, IAMStatement, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions, get_resources

logger = logging.getLogger(__name__)


class SQSLambdaHandler(BaseConnectionHandler):
    """Handles SQS → Lambda connections (event source mapping + permission + IAM)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Generate event source mapping, permission, and attach SQS read IAM."""
        sqs_name = connection.source_name
        lambda_name = connection.target_name
        category = get_category(ServiceType.SQS)

        # --- Event Source Mapping ---
        mapping_name = f"{sqs_name}_{lambda_name}_event_source"
        mapping_attrs: dict[str, str | int] = {
            "event_source_arn": f"aws_sqs_queue.{sqs_name}.arn",
            "function_name": f"aws_lambda_function.{lambda_name}.arn",
            "batch_size": connection.connection_config.get("batch_size", 10),
        }
        batching_window = connection.connection_config.get(
            "maximum_batching_window_in_seconds"
        )
        if batching_window is not None:
            mapping_attrs["maximum_batching_window_in_seconds"] = batching_window

        mapping_content = self._renderer.render_resource(
            "aws_lambda_event_source_mapping", mapping_name, mapping_attrs
        )
        mapping_path = f"{project.project_name}/modules/{category}/sqs/{sqs_name}/event_source_{lambda_name}.tf"

        # --- Lambda Permission ---
        permission_name = f"{sqs_name}_{lambda_name}_permission"
        permission_attrs = {
            "statement_id": f"AllowSQSInvoke_{sqs_name}_{lambda_name}",
            "action": "lambda:InvokeFunction",
            "function_name": f"aws_lambda_function.{lambda_name}.function_name",
            "principal": "sqs.amazonaws.com",
            "source_arn": f"${{aws_sqs_queue.{sqs_name}.arn}}",
        }
        permission_content = self._renderer.render_resource(
            "aws_lambda_permission", permission_name, permission_attrs
        )
        permission_path = f"{project.project_name}/modules/{category}/sqs/{sqs_name}/permission_{lambda_name}.tf"

        # --- IAM statements for the Lambda to receive from SQS ---
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.SQS, "read"),
            resources=get_resources(sqs_name, ServiceType.SQS),
        )
        self._attach_iam_statement(lambda_name, statement, project)

        return [
            GeneratedFile(path=mapping_path, content=mapping_content),
            GeneratedFile(path=permission_path, content=permission_content),
        ]
