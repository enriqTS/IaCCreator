"""Athena queries use native workgroups, exact Glue tables, and S3 result prefixes."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.grafana_athena import RESULT_LOCATION_PATTERN


def athena_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.athena_tables) > 0 && alltrue([for table in values(var.athena_tables) : can(regex("^arn:[^:]+:athena:[^:]+:[0-9]{12}:workgroup/[A-Za-z0-9._-]{1,128}$", table.arn)) && can(regex("^[a-z_][a-z0-9_]{0,254}$", table.database_name)) && can(regex("^[a-z_][a-z0-9_]{0,254}$", table.table_name))])'
            ),
            "error_message": "Grafana requires native Athena workgroup ARNs and concrete Glue database/table names.",
        },
        {
            "condition": Expr(
                'alltrue([for table in values(var.athena_tables) : try(split(":", table.arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", table.arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and connected Athena workgroups must use the same partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for table in values(var.athena_tables) : table.region == try(split(":", table.arn)[3], "") && table.workgroup_name == try(split("/", table.arn)[1], "")])'
            ),
            "error_message": "Athena workgroup names and Regions must match their native ARNs.",
        },
        {
            "condition": Expr(
                f'alltrue([for table in values(var.athena_tables) : table.enforce_configuration && can(regex("{RESULT_LOCATION_PATTERN}", table.output_location))])'
            ),
            "error_message": "Grafana requires enforced workgroup settings and a concrete S3 result prefix ending in /.",
        },
    ]


def athena_query_statements() -> list[dict]:
    return [
        {
            "Sid": "AthenaWorkgroupQueries",
            "Effect": "Allow",
            "Action": [
                "athena:GetWorkGroup",
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StopQueryExecution",
            ],
            "Resource": Expr(
                "distinct([for table in values(var.athena_tables) : table.arn])"
            ),
        },
        {
            "Sid": "AthenaCatalogMetadata",
            "Effect": "Allow",
            "Action": [
                "athena:GetDataCatalog",
                "athena:GetDatabase",
                "athena:ListDatabases",
                "athena:GetTableMetadata",
                "athena:ListTableMetadata",
            ],
            "Resource": Expr(
                'distinct([for table in values(var.athena_tables) : "arn:${split(":", table.arn)[1]}:athena:${table.region}:${split(":", table.arn)[4]}:datacatalog/AwsDataCatalog"])'
            ),
        },
        {
            "Sid": "AthenaRegionalDiscovery",
            "Effect": "Allow",
            "Action": ["athena:ListDataCatalogs", "athena:ListWorkGroups"],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": Expr(
                        "distinct([for table in values(var.athena_tables) : table.region])"
                    )
                }
            },
        },
        {
            "Sid": "AthenaGlueMetadata",
            "Effect": "Allow",
            "Action": [
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:GetTable",
                "glue:GetTables",
                "glue:GetPartition",
                "glue:GetPartitions",
                "glue:BatchGetPartition",
            ],
            "Resource": Expr(
                'distinct(flatten([for table in values(var.athena_tables) : ["arn:${split(":", table.arn)[1]}:glue:${table.region}:${split(":", table.arn)[4]}:catalog", "arn:${split(":", table.arn)[1]}:glue:${table.region}:${split(":", table.arn)[4]}:database/${table.database_name}", "arn:${split(":", table.arn)[1]}:glue:${table.region}:${split(":", table.arn)[4]}:table/${table.database_name}/${table.table_name}"]]))'
            ),
        },
        {
            "Sid": "AthenaResultBucketMetadata",
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
            ],
            "Resource": Expr(
                'distinct([for table in values(var.athena_tables) : "arn:${split(":", table.arn)[1]}:s3:::${try(split("/", table.output_location)[2], "")}"])'
            ),
        },
        {
            "Sid": "AthenaResultObjects",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:AbortMultipartUpload",
                "s3:ListMultipartUploadParts",
            ],
            "Resource": Expr(
                'distinct([for table in values(var.athena_tables) : "arn:${split(":", table.arn)[1]}:s3:::${trimprefix(table.output_location, "s3://")}*"])'
            ),
        },
    ]


def athena_data_sources_expression() -> Expr:
    return Expr("""{
    for binding, tables in { for key, table in var.athena_tables : "${split(":", key)[0]}:${table.database_name}" => table... } : binding => {
      name = length(binding) <= 190 ? binding : "${substr(binding, 0, 173)}-${substr(sha256(binding), 0, 16)}"
      uid = "at-${substr(sha256("${tables[0].arn}/database/${tables[0].database_name}"), 0, 16)}"
      type = "grafana-athena-datasource"
      access = "proxy"
      jsonData = {
        authType = "default"
        defaultRegion = tables[0].region
        catalog = "AwsDataCatalog"
        database = tables[0].database_name
        workgroup = tables[0].workgroup_name
        outputLocation = tables[0].output_location
        resultReuseEnabled = false
      }
    }
  }""")
