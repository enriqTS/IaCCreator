"""Redshift Data API access uses native clusters and selected credential pairs."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.grafana_redshift import REDSHIFT_SELECTOR_PATTERN


def redshift_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.redshift_databases) > 0 && alltrue([for db in values(var.redshift_databases) : can(regex("^arn:[^:]+:redshift:[^:]+:[0-9]{12}:cluster:[a-z][a-z0-9-]{0,62}$", db.arn))])'
            ),
            "error_message": "Grafana requires native provisioned Redshift cluster ARNs.",
        },
        {
            "condition": Expr(
                'alltrue([for db in values(var.redshift_databases) : try(split(":", db.arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", db.arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and Redshift clusters must use the same partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for db in values(var.redshift_databases) : db.region == try(split(":", db.arn)[3], "") && db.cluster_identifier == try(split(":", db.arn)[6], "")])'
            ),
            "error_message": "Redshift cluster identifiers and Regions must match their native ARNs.",
        },
        {
            "condition": Expr(
                f'alltrue([for db in values(var.redshift_databases) : can(regex("{REDSHIFT_SELECTOR_PATTERN}", db.database_name)) && can(regex("{REDSHIFT_SELECTOR_PATTERN}", db.database_user)) && db.database_user != "public" && db.database_user != lower(db.master_username)])'
            ),
            "error_message": "Grafana requires concrete existing Redshift databases and non-administrator users.",
        },
    ]


def redshift_query_statements() -> list[dict | Expr]:
    return [
        {
            "Sid": "RedshiftClusterQueries",
            "Effect": "Allow",
            "Action": [
                "redshift-data:ExecuteStatement",
                "redshift-data:DescribeTable",
                "redshift-data:ListDatabases",
                "redshift-data:ListSchemas",
                "redshift-data:ListTables",
            ],
            "Resource": Expr(
                "distinct([for db in values(var.redshift_databases) : db.arn])"
            ),
        },
        Expr("""[for db in values(var.redshift_databases) : {
      Effect = "Allow"
      Action = ["redshift:GetClusterCredentials"]
      Resource = [
        "arn:${split(":", db.arn)[1]}:redshift:${db.region}:${split(":", db.arn)[4]}:dbuser:${db.cluster_identifier}/${db.database_user}",
        "arn:${split(":", db.arn)[1]}:redshift:${db.region}:${split(":", db.arn)[4]}:dbname:${db.cluster_identifier}/${db.database_name}"
      ]
      Condition = {
        StringEquals = {
          "redshift:DbName" = db.database_name
          "redshift:DbUser" = db.database_user
        }
      }
    }]"""),
        {
            "Sid": "RedshiftStatementResults",
            "Effect": "Allow",
            "Action": [
                "redshift-data:DescribeStatement",
                "redshift-data:GetStatementResult",
                "redshift-data:CancelStatement",
                "redshift-data:ListStatements",
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": Expr(
                        "distinct([for db in values(var.redshift_databases) : db.region])"
                    )
                }
            },
        },
    ]


def redshift_data_sources_expression() -> Expr:
    return Expr("""{
    for binding, db in var.redshift_databases : binding => {
      name = length(binding) <= 190 ? binding : "${substr(binding, 0, 173)}-${substr(sha256(binding), 0, 16)}"
      uid = "rs-${substr(sha256("${db.arn}/database/${db.database_name}/user/${db.database_user}"), 0, 16)}"
      type = "grafana-redshift-datasource"
      access = "proxy"
      jsonData = {
        authType = "default"
        defaultRegion = db.region
        clusterIdentifier = db.cluster_identifier
        database = db.database_name
        dbUser = db.database_user
        useServerless = false
        useManagedSecret = false
        withEvent = false
      }
    }
  }""")
