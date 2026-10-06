"""Logs Insights uses native group identities and region-specific Grafana settings."""

from app.generators.hcl_renderer import Expr


def cloudwatch_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.cloudwatch_log_groups) > 0 && alltrue([for group in values(var.cloudwatch_log_groups) : can(regex("^arn:[^:]+:logs:[^:]+:[0-9]{12}:log-group:[A-Za-z0-9_./#-]+$", trimsuffix(group.arn, ":*")))])'
            ),
            "error_message": "Grafana requires native CloudWatch log-group ARNs.",
        },
        {
            "condition": Expr(
                'alltrue([for group in values(var.cloudwatch_log_groups) : try(split(":", group.arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", group.arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and connected CloudWatch log groups must use the same partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for group in values(var.cloudwatch_log_groups) : group.region == try(split(":", group.arn)[3], "") && group.name == try(split(":", group.arn)[6], "") && contains(["STANDARD", "INFREQUENT_ACCESS"], group.log_group_class)])'
            ),
            "error_message": "CloudWatch names and Regions must match their native log-group identities, using a Logs Insights-supported class.",
        },
        {
            "condition": Expr(
                'alltrue([for group in values(var.cloudwatch_log_groups) : group.kms_key_arn == "" || (can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/[^/]+$", group.kms_key_arn)) && try(split(":", group.kms_key_arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", group.kms_key_arn)[3], "") == group.region)])'
            ),
            "error_message": "Encrypted CloudWatch log groups require a native KMS key ARN in their partition and Region.",
        },
    ]


def cloudwatch_query_statements() -> list[dict | Expr]:
    return [
        {
            "Sid": "CloudWatchLogQueries",
            "Effect": "Allow",
            "Action": [
                "logs:StartQuery",
                "logs:GetQueryResults",
                "logs:GetLogGroupFields",
                "logs:GetLogRecord",
                "logs:FilterLogEvents",
            ],
            "Resource": Expr(
                'flatten([for group in values(var.cloudwatch_log_groups) : [trimsuffix(group.arn, ":*"), "${trimsuffix(group.arn, ":*")}:*"]])'
            ),
        },
        {
            "Sid": "CloudWatchLogEvents",
            "Effect": "Allow",
            "Action": "logs:GetLogEvents",
            "Resource": Expr(
                '[for group in values(var.cloudwatch_log_groups) : "${trimsuffix(group.arn, ":*")}:log-stream:*"]'
            ),
        },
        {
            "Sid": "CloudWatchQueryLifecycle",
            "Effect": "Allow",
            "Action": ["logs:DescribeLogGroups", "logs:StopQuery"],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": Expr(
                        "distinct([for group in values(var.cloudwatch_log_groups) : group.region])"
                    )
                }
            },
        },
        Expr("""[for group in values(var.cloudwatch_log_groups) : {
    Effect = "Allow"
    Action = ["kms:Decrypt"]
    Resource = group.kms_key_arn
    Condition = {
      StringEquals = {
        "kms:ViaService" = "logs.${group.region}.${data.aws_partition.grafana_sources.dns_suffix}"
        "kms:EncryptionContext:aws:logs:arn" = trimsuffix(group.arn, ":*")
      }
    }
  } if group.kms_key_arn != ""]"""),
    ]


def cloudwatch_data_sources_expression() -> Expr:
    return Expr("""{
    for region in distinct([for group in values(var.cloudwatch_log_groups) : group.region]) : region => {
      name = "CloudWatch Logs ${region}"
      uid = "cwlogs-${substr(sha256("${data.aws_caller_identity.grafana_sources.account_id}:${region}"), 0, 16)}"
      type = "cloudwatch"
      access = "proxy"
      jsonData = {
        authType = "default"
        defaultRegion = region
        logGroups = [for group in values(var.cloudwatch_log_groups) : {
          arn = trimsuffix(group.arn, ":*")
          name = group.name
          accountId = split(":", group.arn)[4]
        } if group.region == region]
      }
    }
  }""")
