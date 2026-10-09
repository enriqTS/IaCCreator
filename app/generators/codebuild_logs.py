"""Build-owned logging policies preserve external roles and native destination scope."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.codebuild_logs import (
    KMS_KEY_ARN_PATTERN,
    STREAM_PREFIX_PATTERN,
)
from app.models.iam_role import ROLE_ARN_PATTERN


def build_log_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                f'can(regex("{ROLE_ARN_PATTERN}", var.service_role)) && try(split(":", var.service_role)[1], "") == data.aws_partition.build_logs.partition && try(split(":", var.service_role)[4], "") == data.aws_caller_identity.build_logs.account_id'
            ),
            "error_message": "Build logging requires an external IAM role in the deployment partition and account.",
        },
        {
            "condition": Expr(
                'can(regex("^arn:[^:]+:logs:[^:]+:[0-9]{12}:log-group:[A-Za-z0-9_./#-]{1,512}$", trimsuffix(var.build_logs.arn, ":*"))) && try(split(":", var.build_logs.arn)[1], "") == data.aws_partition.build_logs.partition && try(split(":", var.build_logs.arn)[3], "") == data.aws_region.build_logs.region && try(split(":", var.build_logs.arn)[4], "") == data.aws_caller_identity.build_logs.account_id'
            ),
            "error_message": "Build logs require a native group ARN in the deployment partition, Region, and account.",
        },
        {
            "condition": Expr(
                'var.build_logs.name == try(split(":", var.build_logs.arn)[6], "") && contains(["STANDARD", "INFREQUENT_ACCESS"], var.build_logs.log_group_class)'
            ),
            "error_message": "The native group name must match its ARN and use Standard or Infrequent Access storage.",
        },
        {
            "condition": Expr(
                f'can(regex("{STREAM_PREFIX_PATTERN}", var.build_logs.stream_prefix))'
            ),
            "error_message": "Build log stream prefixes must contain 1–128 letters, numbers, underscores, dots, slashes, hashes, or hyphens.",
        },
        {
            "condition": Expr(
                f'var.build_logs.kms_key_arn == "" || (can(regex("{KMS_KEY_ARN_PATTERN}", var.build_logs.kms_key_arn)) && try(split(":", var.build_logs.kms_key_arn)[1], "") == data.aws_partition.build_logs.partition && try(split(":", var.build_logs.kms_key_arn)[3], "") == data.aws_region.build_logs.region)'
            ),
            "error_message": "Encrypted build logs require a native KMS key ARN in the deployment partition and Region.",
        },
    ]


def build_log_statements(renderer: HCLRenderer) -> Expr:
    service = Expr(
        '"logs.${data.aws_region.build_logs.region}.${data.aws_partition.build_logs.dns_suffix}"'
    )
    crypto = {
        "Effect": "Allow",
        "Action": [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
        ],
        "Resource": Expr("key"),
        "Condition": {
            "StringEquals": {
                "kms:ViaService": service,
                "kms:EncryptionContext:aws:logs:arn": Expr(
                    'trimsuffix(var.build_logs.arn, ":*")'
                ),
            }
        },
    }
    describe = {
        "Effect": "Allow",
        "Action": ["kms:DescribeKey"],
        "Resource": Expr("key"),
        "Condition": {"StringEquals": {"kms:ViaService": service}},
    }
    statements = [
        {
            "Effect": "Allow",
            "Action": ["logs:CreateLogGroup"],
            "Resource": Expr('trimsuffix(var.build_logs.arn, ":*")'),
        },
        {
            "Effect": "Allow",
            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
            "Resource": Expr(
                '"${trimsuffix(var.build_logs.arn, ":*")}:log-stream:${var.build_logs.stream_prefix}*"'
            ),
        },
        *[
            Expr(
                f"[for key in compact([var.build_logs.kms_key_arn]) : {renderer.render_expression(statement, depth=4)}]"
            )
            for statement in (crypto, describe)
        ],
    ]
    return Expr(f"flatten({renderer.render_expression(statements, depth=3)})")


def add_build_log_attributes(attrs: dict) -> None:
    attrs["logs_config"] = {
        "cloudwatch_logs": {
            "status": "ENABLED",
            "group_name": Expr("var.build_logs.name"),
            "stream_name": Expr("var.build_logs.stream_prefix"),
        },
    }
    dependencies = str(attrs.get("depends_on", "[]"))[1:-1]
    attrs["depends_on"] = Expr(
        f"[{dependencies}{', ' if dependencies else ''}aws_iam_role_policy.build_logs]"
    )
    attrs["lifecycle"] = {"precondition": build_log_preconditions()}


def render_build_log_resources(renderer: HCLRenderer) -> str:
    content = 'data "aws_partition" "build_logs" {}\ndata "aws_region" "build_logs" {}\ndata "aws_caller_identity" "build_logs" {}\n\ndata "aws_iam_role" "build_logs" {\n  name = element(reverse(split("/", var.service_role)), 0)\n}\n\n'
    return content + renderer.render_resource(
        "aws_iam_role_policy",
        "build_logs",
        {
            "name_prefix": "build-logs-",
            "role": Expr("data.aws_iam_role.build_logs.name"),
            "policy": renderer.render_json_policy(
                {"Version": "2012-10-17", "Statement": build_log_statements(renderer)},
                depth=2,
            ),
            "lifecycle": {
                "precondition": [
                    *build_log_preconditions(),
                    {
                        "condition": Expr(
                            "data.aws_iam_role.build_logs.arn == var.service_role"
                        ),
                        "error_message": "The resolved build service role ARN must exactly match the configured role, including its path.",
                    },
                ]
            },
        },
    )
