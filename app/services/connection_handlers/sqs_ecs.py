"""Queue-scoped polling permissions and runtime references for ECS task code."""

from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_consumer import KmsConsumerGrants


class SQSECSHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="ECS application code must poll the exported queue URL, process messages, delete successful messages, and extend visibility when needed. This connection grants the task role access; it creates no event source mapping, polling worker, autoscaling, or container environment variables. Configure long polling, retries, visibility timeout, and network access separately. KMS key policies must permit the task role; retained messages encrypted with previous or dead-letter source keys need those key permissions separately.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        queue, consumer = connection.source_name, connection.target_name
        result = ConnectionContribution()
        for attribute in ("arn", "url"):
            variable = f"sqs_{queue}_{attribute}"
            result.inputs.append(
                ModuleInput(
                    module=consumer,
                    name=variable,
                    value=f"module.{queue}.queue_{attribute}",
                    description="Queue identity for the ECS polling application",
                )
            )
            result.outputs.append(self._output(consumer, variable, f"var.{variable}"))
        result.outputs.append(
            self._output(
                consumer,
                f"sqs_{queue}_region",
                f'split(":", var.sqs_{queue}_arn)[3]',
                "AWS region for the queue client",
            )
        )
        result.iam.append(
            self._grant(
                consumer,
                IAMStatement(
                    actions=[
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:ChangeMessageVisibility",
                        "sqs:GetQueueAttributes",
                    ],
                    resources=["${var.sqs_" + queue + "_arn}"],
                ),
            )
        )
        return KmsConsumerGrants().augment(result, queue, project)
