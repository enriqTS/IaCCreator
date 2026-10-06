"""Bind Config delivery channels to unencrypted, policy-ready SNS topics."""

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
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
from app.services.connection_handlers.topic_delivery_policy import (
    TOPIC_DELIVERY_POLICY,
    TopicDeliveryPolicy,
)


class AwsConfigSnsHandler(BaseConnectionHandler):
    def _check_destination(self, connection: ConnectionIR, project: ProjectIR) -> None:
        recorder = self._find_instance(connection.source_name, project)
        topic = self._find_instance(connection.target_name, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == recorder.name
            and item.target_service == ServiceType.SNS
            and item.connection_type == "notifies"
        ]
        error = None
        field = "target"
        if len({item.target_name for item in peers}) > 1:
            error = "An AWS Config delivery channel supports only one SNS topic"
        elif topic.config.fifo_topic or (topic.config.topic_name or "").endswith(
            ".fifo"
        ):
            field = "fifo_topic"
            error = "AWS Config requires a standard SNS topic"
        elif topic.config.kms_master_key_id or any(
            item.source_service == ServiceType.KMS
            and item.target_name == topic.name
            and item.connection_type == "encrypts"
            for item in project.connections
        ):
            field = "kms_master_key_id"
            error = "AWS Config does not support encrypted SNS topics"
        if error:
            raise InvalidConnectionConfigError(
                recorder.name,
                topic.name,
                connection.connection_type,
                [{"loc": (field,), "msg": error}],
            )
        for environment in project.environments:
            override = environment.variables.get("region")
            source_region = (
                override
                or recorder.provider_region
                or project.global_config.provider_region
            )
            target_region = (
                override
                or topic.provider_region
                or project.global_config.provider_region
            )
            if source_region != target_region:
                raise CrossRegionConnectionError(
                    recorder.name,
                    source_region,
                    topic.name,
                    target_region,
                    connection.connection_type,
                )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        self._check_destination(connection, project)
        name = connection.source_name
        self._find_instance(name, project).config._sns_notifications = True
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=name,
                    name="sns_topic_arn",
                    value=f"module.{connection.target_name}.config_notification_arn",
                    description="SNS topic available after Config delivery permissions",
                )
            ],
            outputs=[
                self._output(
                    name,
                    "notification_source_account_id",
                    "data.aws_caller_identity.config_notifications.account_id",
                    "Config notification source account",
                ),
                self._output(
                    name,
                    "notification_source_arn",
                    '"arn:${data.aws_partition.config_notifications.partition}:config:${data.aws_region.config_notifications.region}:${data.aws_caller_identity.config_notifications.account_id}:*"',
                    "Config service notification source scope",
                ),
                ModuleOutput(
                    module=connection.target_name,
                    name="config_notification_arn",
                    value=f"aws_sns_topic.{connection.target_name}.arn",
                    description="Topic ready for Config notifications",
                    depends_on=[TOPIC_DELIVERY_POLICY],
                ),
            ],
            resources=[
                self._resource(
                    name,
                    "config_notifications.tf",
                    'data "aws_partition" "config_notifications" {}\ndata "aws_region" "config_notifications" {}\ndata "aws_caller_identity" "config_notifications" {}\n',
                )
            ],
        )
        result.merge(TopicDeliveryPolicy().handle(connection, project))
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._check_destination(connection, project)
        recorder = self._find_instance(connection.source_name, project)
        issues = []
        if not recorder.config.role_arn:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="AWS Config still requires a recorder IAM role with recording permissions. Configure role_arn before applying.",
                )
            )
        if not recorder.config.s3_bucket_name and not any(
            item.source_name == recorder.name
            and item.target_service == ServiceType.S3
            and item.connection_type == "delivers_to"
            for item in project.connections
        ):
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="AWS Config still requires an S3 delivery bucket. Configure s3_bucket_name or connect a managed bucket before applying.",
                )
            )
        return issues
