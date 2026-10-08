"""X-Ray read permissions are regional; native groups supply query defaults."""

from app.generators.hcl_renderer import Expr
from app.generators.xray_filters import (
    XRAY_GROUP_NAME_PATTERN as XRAY_GROUP_NAME_PATTERN,
)


def xray_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.xray_groups) > 0 && alltrue([for group in values(var.xray_groups) : can(regex("^arn:[^:]+:xray:[^:]+:[0-9]{12}:group/[A-Za-z0-9_-]{1,32}/[A-Za-z0-9_-]+$", group.arn))])'
            ),
            "error_message": "Grafana requires native X-Ray group ARNs.",
        },
        {
            "condition": Expr(
                'alltrue([for group in values(var.xray_groups) : try(split(":", group.arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", group.arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and X-Ray groups must use the same partition and account.",
        },
        {
            "condition": Expr(
                f'alltrue([for group in values(var.xray_groups) : group.region == try(split(":", group.arn)[3], "") && group.name == try(split("/", group.arn)[1], "") && can(regex("{XRAY_GROUP_NAME_PATTERN}", group.name)) && group.name != "Default" && length(trimspace(group.filter_expression)) > 0])'
            ),
            "error_message": "X-Ray group names and Regions must match their native identities and have a nonempty query filter.",
        },
    ]


def xray_query_statements() -> list[dict | Expr]:
    regions = Expr("distinct([for group in values(var.xray_groups) : group.region])")
    return [
        {
            "Sid": "XRayTraceReads",
            "Effect": "Allow",
            "Action": [
                "xray:BatchGetTraces",
                "xray:GetTraceSummaries",
                "xray:GetTraceGraph",
                "xray:GetGroups",
                "xray:GetTimeSeriesServiceStatistics",
                "xray:GetServiceGraph",
            ],
            "Resource": "*",
            "Condition": {"StringEquals": {"aws:RequestedRegion": regions}},
        },
        {
            "Sid": "XRayRegionDiscovery",
            "Effect": "Allow",
            "Action": ["ec2:DescribeRegions"],
            "Resource": "*",
            "Condition": {"StringEquals": {"aws:RequestedRegion": regions}},
        },
        Expr("""anytrue([for group in values(var.xray_groups) : group.insights_enabled]) ? [{
      Sid = "XRayInsightReads"
      Effect = "Allow"
      Action = ["xray:GetInsightSummaries", "xray:GetInsight"]
      Resource = "*"
      Condition = {
        StringEquals = {
          "aws:RequestedRegion" = distinct([for group in values(var.xray_groups) : group.region if group.insights_enabled])
        }
      }
    }] : []"""),
    ]


def _regional_uid(region: str) -> str:
    return f'"xr-${{substr(sha256("${{data.aws_partition.grafana_sources.partition}}:${{data.aws_caller_identity.grafana_sources.account_id}}:${{{region}}}"), 0, 16)}}"'


def xray_data_sources_expression() -> Expr:
    return Expr(
        """{
    for region in distinct([for group in values(var.xray_groups) : group.region]) : region => {
      name = "X-Ray ${region}"
      uid = REGIONAL_UID
      type = "grafana-x-ray-datasource"
      access = "proxy"
      jsonData = {
        authType = "default"
        defaultRegion = region
      }
    }
  }""".replace("REGIONAL_UID", _regional_uid("region"))
    )


def xray_query_defaults_expression() -> Expr:
    return Expr(
        """{
    for binding, group in var.xray_groups : binding => {
      datasource_uid = REGIONAL_UID
      queries = merge({
        trace_summaries = {
          refId = "A"
          queryMode = "X-Ray"
          queryType = "getTraceSummaries"
          region = group.region
          query = group.filter_expression
        }
        service_map = {
          refId = "A"
          queryMode = "X-Ray"
          queryType = "getServiceMap"
          region = group.region
          query = ""
          group = {
            GroupARN = group.arn
            GroupName = group.name
            FilterExpression = group.filter_expression
          }
        }
      }, group.insights_enabled ? {
        insights = {
          refId = "A"
          queryMode = "X-Ray"
          queryType = "getInsights"
          region = group.region
          query = ""
          state = "All"
          group = {
            GroupARN = group.arn
            GroupName = group.name
            FilterExpression = group.filter_expression
          }
        }
      } : {})
    }
  }""".replace("REGIONAL_UID", _regional_uid("group.region"))
    )
