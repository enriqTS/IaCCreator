"""Service-specific key-policy requirements and their connected identities."""

from collections.abc import Callable
from dataclasses import dataclass

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR


def principal(service: str) -> dict:
    return {
        "Service": Expr(f'"{service}.${{data.aws_partition.kms_policy.dns_suffix}}"')
    }


def cloudtrail(arns: Expr) -> list[dict]:
    return [
        {
            "Sid": "CloudTrailEncryption",
            "Effect": "Allow",
            "Principal": principal("cloudtrail"),
            "Action": "kms:GenerateDataKey*",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceArn": arns,
                    "kms:EncryptionContext:aws:cloudtrail:arn": arns,
                }
            },
        },
        {
            "Sid": "CloudTrailDescribe",
            "Effect": "Allow",
            "Principal": principal("cloudtrail"),
            "Action": "kms:DescribeKey",
            "Resource": "*",
            "Condition": {"StringEquals": {"aws:SourceArn": arns}},
        },
    ]


def logs(arns: Expr) -> list[dict]:
    return [
        {
            "Sid": "CloudWatchLogsEncryption",
            "Effect": "Allow",
            "Principal": principal("logs.${data.aws_region.kms_policy.region}"),
            "Action": [
                "kms:Encrypt",
                "kms:Decrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
                "kms:DescribeKey",
            ],
            "Resource": "*",
            "Condition": {"ArnEquals": {"kms:EncryptionContext:aws:logs:arn": arns}},
        }
    ]


def sns(arns: Expr) -> list[dict]:
    return [
        {
            "Sid": "SnsQueueDelivery",
            "Effect": "Allow",
            "Principal": principal("sns"),
            "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
            "Resource": "*",
            "Condition": {"ArnEquals": {"aws:SourceArn": arns}},
        }
    ]


def eventbridge(_arns: Expr) -> list[dict]:
    return [
        {
            "Sid": "EventBridgeQueueDelivery",
            "Effect": "Allow",
            "Principal": principal("events"),
            "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
            "Resource": "*",
        }
    ]


def s3(_arns: Expr) -> list[dict]:
    return [
        {
            "Effect": "Allow",
            "Principal": principal("s3"),
            "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
            "Resource": "*",
        }
    ]


@dataclass(frozen=True)
class KeyPolicyRule:
    encrypted_service: ServiceType
    variable: str | None
    statements: Callable[[Expr], list[dict]]
    publisher: ServiceType | None = None

    def members(self, key: str, project: ProjectIR) -> set[str]:
        targets = {
            item.target_name
            for item in project.connections
            if item.source_name == key
            and item.source_service == ServiceType.KMS
            and item.target_service == self.encrypted_service
            and item.connection_type == "encrypts"
        }
        if self.publisher is None:
            return targets
        return {
            item.source_name
            for item in project.connections
            if item.target_name in targets
            and item.source_service == self.publisher
            and item.target_service == self.encrypted_service
        }


def cloudfront(arns: Expr) -> list[dict]:
    return [
        {
            "Effect": "Allow",
            "Principal": principal("cloudfront"),
            "Action": "kms:Decrypt",
            "Resource": "*",
            "Condition": {"StringEquals": {"aws:SourceArn": arns}},
        }
    ]


POLICY_RULES = (
    KeyPolicyRule(
        ServiceType.S3, "s3_distribution_arns", cloudfront, ServiceType.CLOUDFRONT
    ),
    KeyPolicyRule(ServiceType.SQS, None, s3, ServiceType.S3),
    KeyPolicyRule(ServiceType.SNS, None, s3, ServiceType.S3),
    KeyPolicyRule(ServiceType.CLOUDTRAIL, "cloudtrail_arns", cloudtrail),
    KeyPolicyRule(ServiceType.CLOUDWATCH, "log_group_arns", logs),
    KeyPolicyRule(ServiceType.SQS, "sqs_publisher_topic_arns", sns, ServiceType.SNS),
    KeyPolicyRule(ServiceType.SQS, None, eventbridge, ServiceType.EVENTBRIDGE),
)
