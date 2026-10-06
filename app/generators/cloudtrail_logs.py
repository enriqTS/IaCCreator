"""CloudTrail delivery attributes, stream permissions, and native scope guards."""

from app.generators.hcl_renderer import Expr, HCLRenderer


def cloudtrail_logs_preconditions() -> list[dict]:
    arn = 'trimsuffix(var.cloud_watch_logs_group_arn, ":*")'
    return [
        {
            "condition": Expr(
                f'can(regex("^arn:[^:]+:logs:[^:]+:[0-9]{{12}}:log-group:[A-Za-z0-9_./#-]+$", {arn}))'
            ),
            "error_message": "CloudTrail requires a CloudWatch log-group ARN.",
        },
        {
            "condition": Expr(
                f'try(split(":", {arn})[1], "") == data.aws_partition.cloudtrail_logs.partition && try(split(":", {arn})[3], "") == data.aws_region.cloudtrail_logs.region'
            ),
            "error_message": "CloudTrail and its CloudWatch log group must use the same partition and home Region.",
        },
        {
            "condition": Expr(
                f'try(split(":", {arn})[4], "") == data.aws_caller_identity.cloudtrail_logs.account_id'
            ),
            "error_message": "CloudTrail and its CloudWatch log group must belong to the same account.",
        },
    ]


def cloudtrail_logs_attributes(name: str) -> dict:
    return {
        "cloud_watch_logs_group_arn": Expr(
            '"${trimsuffix(var.cloud_watch_logs_group_arn, ":*")}:*"'
        ),
        "cloud_watch_logs_role_arn": Expr(f"aws_iam_role.{name}_cloudwatch_logs.arn"),
        "depends_on": [Expr(f"aws_iam_role_policy.{name}_cloudwatch_logs")],
        "lifecycle": {"precondition": cloudtrail_logs_preconditions()},
    }


def cloudtrail_log_stream_arn() -> Expr:
    return Expr(
        '"${trimsuffix(var.cloud_watch_logs_group_arn, ":*")}:log-stream:${data.aws_caller_identity.cloudtrail_logs.account_id}_CloudTrail_${var.is_multi_region_trail ? "" : data.aws_region.cloudtrail_logs.region}*"'
    )


def render_cloudtrail_logs_role(
    name: str, statements: list[dict], renderer: HCLRenderer
) -> str:
    resource = f"{name}_cloudwatch_logs"
    content = 'data "aws_partition" "cloudtrail_logs" {}\ndata "aws_region" "cloudtrail_logs" {}\ndata "aws_caller_identity" "cloudtrail_logs" {}\n\n'
    content += renderer.render_resource(
        "aws_iam_role",
        resource,
        {
            "name_prefix": "cloudtrail-logs-",
            "assume_role_policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Principal": {
                                "Service": Expr(
                                    '"cloudtrail.${data.aws_partition.cloudtrail_logs.dns_suffix}"'
                                )
                            },
                        }
                    ],
                }
            ),
        },
    )
    content += "\n" + renderer.render_resource(
        "aws_iam_role_policy",
        resource,
        {
            "name_prefix": "cloudtrail-delivery-",
            "role": Expr(f"aws_iam_role.{resource}.id"),
            "policy": renderer.render_json_policy(
                {"Version": "2012-10-17", "Statement": statements}
            ),
        },
    )
    return content
