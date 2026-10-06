"""Aggregate S3 and Config delivery permissions in one topic-owned policy."""

from app.generators.aws_config_notifications import config_topic_preconditions
from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler

TOPIC_DELIVERY_POLICY = "aws_sns_topic_policy.s3_delivery"


class TopicDeliveryPolicy(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        topic = connection.target_name
        peers = [
            item
            for item in project.connections
            if item.target_name == topic
            and item.target_service == ServiceType.SNS
            and item.source_service in (ServiceType.S3, ServiceType.AWS_CONFIG)
            and item.connection_type == "notifies"
        ]
        buckets = sorted(
            {
                item.source_name
                for item in peers
                if item.source_service == ServiceType.S3
            }
        )
        recorders = sorted(
            {
                item.source_name
                for item in peers
                if item.source_service == ServiceType.AWS_CONFIG
            }
        )
        result = ConnectionContribution()
        arn = Expr(f"aws_sns_topic.{topic}.arn")
        statements = [
            {
                "Sid": "OwnerAccess",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": [
                    "SNS:GetTopicAttributes",
                    "SNS:SetTopicAttributes",
                    "SNS:AddPermission",
                    "SNS:RemovePermission",
                    "SNS:DeleteTopic",
                    "SNS:Subscribe",
                    "SNS:ListSubscriptionsByTopic",
                    "SNS:Publish",
                ],
                "Resource": arn,
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceOwner": Expr(
                            "data.aws_caller_identity.topic_delivery.account_id"
                        )
                    }
                },
            }
        ]
        if buckets:
            result.inputs.append(
                ModuleInput(
                    module=topic,
                    name="notification_bucket_arns",
                    type="list(string)",
                    value="["
                    + ", ".join(f"module.{bucket}.bucket_arn" for bucket in buckets)
                    + "]",
                    description="Buckets authorized to publish notifications",
                )
            )
            statements.append(
                {
                    "Sid": "S3Delivery",
                    "Effect": "Allow",
                    "Principal": {"Service": "s3.amazonaws.com"},
                    "Action": "SNS:Publish",
                    "Resource": arn,
                    "Condition": {
                        "ArnEquals": {
                            "aws:SourceArn": Expr("var.notification_bucket_arns")
                        }
                    },
                }
            )
        for index, recorder in enumerate(recorders):
            for field in ("account_id", "arn"):
                result.inputs.append(
                    ModuleInput(
                        module=topic,
                        name=f"config_{recorder}_source_{field}",
                        value=f"module.{recorder}.notification_source_{field}",
                        description="AWS Config source identity before channel creation",
                    )
                )
            statements.append(
                {
                    "Sid": f"ConfigDelivery{index}",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": Expr(
                            '"config.${data.aws_partition.topic_delivery.dns_suffix}"'
                        )
                    },
                    "Action": "SNS:Publish",
                    "Resource": arn,
                    "Condition": {
                        "StringEquals": {
                            "AWS:SourceAccount": Expr(
                                f"var.config_{recorder}_source_account_id"
                            )
                        },
                        "ArnLike": {
                            "AWS:SourceArn": Expr(f"var.config_{recorder}_source_arn")
                        },
                    },
                }
            )
        attrs = {
            "arn": arn,
            "policy": self._renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Id": Expr(f'"${{aws_sns_topic.{topic}.arn}}/delivery"'),
                    "Statement": statements,
                }
            ),
        }
        if recorders:
            attrs["lifecycle"] = {"precondition": config_topic_preconditions(topic)}
        result.resources.append(
            self._resource(
                topic,
                "policy_s3_delivery.tf",
                'data "aws_caller_identity" "topic_delivery" {}\ndata "aws_partition" "topic_delivery" {}\n\n'
                + self._renderer.render_resource(
                    "aws_sns_topic_policy", "s3_delivery", attrs
                ),
            )
        )
        return result
