"""Wire asynchronous Lambda failures to one standard queue or topic."""

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_consumer import KmsConsumerGrants


class LambdaDeadLetterHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Captures discarded asynchronous Lambda events only. Synchronous calls and SQS event-source retries need their own error handling. Configure retries, retention, consumers or SNS subscriptions, replay, and DeadLetterErrors alarms separately. Avoid routing failures back into the same function. Destination message-size limits and KMS key policies can prevent delivery; the execution role receives scoped send/publish and applicable key permissions.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = self._find_instance(connection.source_name, project)
        target = self._find_instance(connection.target_name, project)
        destinations = {
            item.target_name
            for item in project.connections
            if item.source_name == source.name
            and item.connection_type == "dead_letters_to"
        }
        if len(destinations) != 1:
            self._reject(
                connection,
                "A Lambda function can have only one dead-letter destination",
            )
        if source.config.dead_letter_target_arn is not None:
            self._reject(
                connection,
                "Remove the external dead_letter_target_arn before connecting a managed destination",
            )
        if source.config.is_layer:
            self._reject(
                connection, "Lambda layers cannot have dead-letter destinations"
            )
        is_queue = target.service_type == ServiceType.SQS
        if getattr(target.config, "fifo_queue" if is_queue else "fifo_topic", False):
            self._reject(
                connection,
                "Lambda dead-letter destinations must be standard queues or topics, not FIFO",
            )
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="dead_letter_target_arn",
                    value=f"module.{target.name}.{'queue' if is_queue else 'topic'}_arn",
                )
            ],
            iam=[
                self._grant(
                    source.name,
                    IAMStatement(
                        actions=["sqs:SendMessage" if is_queue else "sns:Publish"],
                        resources=["${var.dead_letter_target_arn}"],
                    ),
                )
            ],
        )
        return KmsConsumerGrants().augment(result, target.name, project)

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("dead_letter",), "msg": message}],
        )
