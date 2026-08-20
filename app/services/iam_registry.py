"""Single source of truth for per-service IAM action definitions."""

from app.exceptions import GeneratorConfigError
from app.models.input_models import ServiceType

# Full IAM actions per target service type (read + write combined)
IAM_ACTIONS: dict[ServiceType, list[str]] = {
    ServiceType.DYNAMODB: [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
    ],
    ServiceType.S3: [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
    ],
    ServiceType.CLOUDWATCH: [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    ],
    ServiceType.SNS: ["sns:Publish"],
    ServiceType.SQS: ["sqs:SendMessage"],
}

# Consuming a change stream, which is a distinct set of actions from table access
IAM_STREAM_ACTIONS: dict[ServiceType, list[str]] = {
    ServiceType.DYNAMODB: [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams",
    ],
}

# Read-only access-pattern variants
IAM_READ_ACTIONS: dict[ServiceType, list[str]] = {
    ServiceType.DYNAMODB: [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
    ],
    ServiceType.S3: [
        "s3:GetObject",
        "s3:ListBucket",
    ],
    ServiceType.CLOUDWATCH: [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    ],
    ServiceType.SNS: ["sns:Publish"],
    ServiceType.SQS: [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
    ],
}

# Write-only access-pattern variants
IAM_WRITE_ACTIONS: dict[ServiceType, list[str]] = {
    ServiceType.DYNAMODB: [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
    ],
    ServiceType.S3: [
        "s3:PutObject",
        "s3:DeleteObject",
    ],
    ServiceType.CLOUDWATCH: [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    ],
    ServiceType.SNS: ["sns:Publish"],
    ServiceType.SQS: ["sqs:SendMessage"],
}


def get_actions(service_type: ServiceType, access_pattern: str = "full") -> list[str]:
    """Return the IAM actions for a service type and access pattern."""
    table = {
        "read": IAM_READ_ACTIONS,
        "write": IAM_WRITE_ACTIONS,
        "stream": IAM_STREAM_ACTIONS,
    }.get(access_pattern, IAM_ACTIONS)

    actions = table.get(service_type)
    if actions is None:
        raise GeneratorConfigError(
            f"No IAM actions registered for service '{service_type.value}' "
            f"with access pattern '{access_pattern}'"
        )
    return actions


def get_resources(target_name: str, target_service: ServiceType) -> list[str]:
    """Build the ARN references an IAM statement should target."""
    if target_service == ServiceType.DYNAMODB:
        return [f"${{aws_dynamodb_table.{target_name}.arn}}"]
    elif target_service == ServiceType.S3:
        return [
            f"${{aws_s3_bucket.{target_name}.arn}}",
            f"${{aws_s3_bucket.{target_name}.arn}}/*",
        ]
    elif target_service == ServiceType.CLOUDWATCH:
        return [f"arn:aws:logs:*:*:log-group:/aws/lambda/{target_name}:*"]
    elif target_service == ServiceType.SNS:
        return [f"${{aws_sns_topic.{target_name}.arn}}"]
    elif target_service == ServiceType.SQS:
        return [f"${{aws_sqs_queue.{target_name}.arn}}"]
    return []
