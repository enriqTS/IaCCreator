"""S3 delivery permissions are owned by the destination module."""

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
    require_custom_delivery_key,
)
from app.services.connection_handlers.queue_delivery_policy import QueueDeliveryPolicy
from app.services.connection_handlers.s3_notifications import S3Notifications
from app.services.connection_handlers.topic_delivery_policy import (
    TOPIC_DELIVERY_POLICY,
    TopicDeliveryPolicy,
)


class S3DestinationHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return external_service_key_issues(connection, project)

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        service = connection.target_service
        fifo_field = "fifo_queue" if service == ServiceType.SQS else "fifo_topic"
        if getattr(target.config, fifo_field, False):
            raise InvalidConnectionConfigError(
                connection.source_name,
                target.name,
                connection.connection_type,
                [
                    {
                        "loc": (fifo_field,),
                        "msg": "S3 notifications require a standard SNS topic or SQS queue",
                    }
                ],
            )
        require_custom_delivery_key(connection, project)
        resource = "aws_sqs_queue" if service == ServiceType.SQS else "aws_sns_topic"
        policy = (
            "aws_sqs_queue_policy.delivery"
            if service == ServiceType.SQS
            else TOPIC_DELIVERY_POLICY
        )
        result = ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    target.name,
                    "notification_arn",
                    f"module.{target.name}.s3_notification_arn",
                    "Destination ARN available after delivery permissions",
                )
            ],
            outputs=[
                ModuleOutput(
                    module=target.name,
                    name="s3_notification_arn",
                    value=f"{resource}.{target.name}.arn",
                    description="Destination ready for S3 notifications",
                    depends_on=[policy],
                )
            ],
        )
        if service == ServiceType.SQS:
            result.merge(QueueDeliveryPolicy().handle(connection, project))
        else:
            result.merge(TopicDeliveryPolicy().handle(connection, project))
        result.merge(S3Notifications().handle(connection, project))
        return result
