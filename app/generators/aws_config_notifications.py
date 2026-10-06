"""Native delivery-channel guards preserve Config's supported SNS scope."""

from app.generators.hcl_renderer import Expr


def config_sns_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'can(regex("^arn:[^:]+:sns:[^:]+:[0-9]{12}:[A-Za-z0-9_-]+$", var.sns_topic_arn))'
            ),
            "error_message": "AWS Config requires a standard SNS topic ARN.",
        },
        {
            "condition": Expr(
                'try(split(":", var.sns_topic_arn)[1], "") == data.aws_partition.config_notifications.partition && try(split(":", var.sns_topic_arn)[3], "") == data.aws_region.config_notifications.region'
            ),
            "error_message": "AWS Config and its SNS topic must use the same partition and Region.",
        },
    ]


def config_topic_preconditions(topic: str) -> list[dict]:
    resource = f"aws_sns_topic.{topic}"
    return [
        {
            "condition": Expr(f"{resource}.fifo_topic != true"),
            "error_message": "AWS Config requires a standard SNS topic.",
        },
        {
            "condition": Expr(
                f'{resource}.kms_master_key_id == null || {resource}.kms_master_key_id == ""'
            ),
            "error_message": "AWS Config does not support encrypted SNS topics.",
        },
    ]
