"""Single source of truth for per-service IAM action definitions."""

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


def get_actions(
    service_type: ServiceType, access_pattern: str = "full"
) -> list[str] | None:
    """Return IAM actions for a service type and access pattern, or None if not registered.

    Args:
        service_type: The target AWS service type.
        access_pattern: One of "full", "read", or "write".

    Returns:
        List of IAM action strings, or None if the service type has no entry.
    """
    if access_pattern == "read":
        return IAM_READ_ACTIONS.get(service_type)
    elif access_pattern == "write":
        return IAM_WRITE_ACTIONS.get(service_type)
    return IAM_ACTIONS.get(service_type)


def get_resources(target_name: str, target_service: ServiceType) -> list[str]:
    """Build Terraform resource references for IAM statement resources.

    Args:
        target_name: The name of the target resource.
        target_service: The service type of the target resource.

    Returns:
        List of Terraform resource ARN references.
    """
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
