"""S3 delivery permissions are owned by the destination module."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
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
            else "aws_sns_topic_policy.s3_delivery"
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
            result.merge(S3TopicPolicy().handle(connection, project))
        result.merge(S3Notifications().handle(connection, project))
        return result


class S3TopicPolicy(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        topic = connection.target_name
        buckets = sorted(
            {
                item.source_name
                for item in project.connections
                if item.source_service == ServiceType.S3
                and item.target_name == topic
                and item.connection_type == "notifies"
            }
        )
        policy = self._renderer.render_json_policy(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "s3.amazonaws.com"},
                        "Action": "SNS:Publish",
                        "Resource": Expr(f"aws_sns_topic.{topic}.arn"),
                        "Condition": {
                            "ArnEquals": {
                                "aws:SourceArn": Expr("var.notification_bucket_arns")
                            }
                        },
                    }
                ],
            }
        )
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=topic,
                    name="notification_bucket_arns",
                    type="list(string)",
                    value="["
                    + ", ".join(f"module.{bucket}.bucket_arn" for bucket in buckets)
                    + "]",
                    description="Buckets authorized to publish notifications",
                )
            ],
            resources=[
                self._resource(
                    topic,
                    "policy_s3_delivery.tf",
                    self._renderer.render_resource(
                        "aws_sns_topic_policy",
                        "s3_delivery",
                        {"arn": Expr(f"aws_sns_topic.{topic}.arn"), "policy": policy},
                    ),
                )
            ],
        )
