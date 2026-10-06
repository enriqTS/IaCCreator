"""Timestream queries use selected tables and native regional database identities."""

from app.generators.hcl_renderer import Expr


def timestream_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.timestream_tables) > 0 && alltrue([for table in values(var.timestream_tables) : can(regex("^arn:[^:]+:timestream:[^:]+:[0-9]{12}:database/[A-Za-z0-9_.-]{3,256}$", table.database_arn)) && can(regex("^[A-Za-z0-9_.-]{3,256}$", table.table_name))])'
            ),
            "error_message": "Grafana requires native Timestream database ARNs and explicit table names without IAM wildcards.",
        },
        {
            "condition": Expr(
                'alltrue([for table in values(var.timestream_tables) : try(split(":", table.database_arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", table.database_arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and connected Timestream databases must use the same partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for table in values(var.timestream_tables) : table.region == try(split(":", table.database_arn)[3], "") && table.database_name == try(split("/", table.database_arn)[1], "")])'
            ),
            "error_message": "Timestream database names and Regions must match their native database identities.",
        },
    ]


def timestream_query_statements() -> list[dict]:
    return [
        {
            "Sid": "TimestreamTableQueries",
            "Effect": "Allow",
            "Action": [
                "timestream:Select",
                "timestream:DescribeTable",
                "timestream:ListMeasures",
            ],
            "Resource": Expr(
                'distinct([for table in values(var.timestream_tables) : "${table.database_arn}/table/${table.table_name}"])'
            ),
        },
        {
            "Sid": "TimestreamDatabaseMetadata",
            "Effect": "Allow",
            "Action": ["timestream:DescribeDatabase", "timestream:ListTables"],
            "Resource": Expr(
                "distinct([for table in values(var.timestream_tables) : table.database_arn])"
            ),
        },
        {
            "Sid": "TimestreamRegionalDiscovery",
            "Effect": "Allow",
            "Action": [
                "timestream:DescribeEndpoints",
                "timestream:ListDatabases",
                "timestream:SelectValues",
                "timestream:CancelQuery",
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": Expr(
                        "distinct([for table in values(var.timestream_tables) : table.region])"
                    )
                }
            },
        },
    ]


def timestream_data_sources_expression() -> Expr:
    return Expr("""{
    for binding, table in var.timestream_tables : binding => {
      name = length(binding) <= 190 ? binding : "${substr(binding, 0, 173)}-${substr(sha256(binding), 0, 16)}"
      uid = "ts-${substr(sha256("${table.database_arn}/table/${table.table_name}"), 0, 16)}"
      type = "grafana-timestream-datasource"
      access = "proxy"
      jsonData = {
        authType = "default"
        defaultRegion = table.region
        defaultDatabase = jsonencode(table.database_name)
        defaultTable = jsonencode(table.table_name)
      }
    }
  }""")
