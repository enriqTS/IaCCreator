"""Prometheus query settings use native identities and credential-free SigV4."""

from app.generators.hcl_renderer import Expr


def prometheus_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.prometheus_workspaces) > 0 && alltrue([for workspace in values(var.prometheus_workspaces) : can(regex("^arn:[^:]+:aps:[^:]+:[0-9]{12}:workspace/ws-[0-9a-f-]+$", workspace.arn))])'
            ),
            "error_message": "Grafana requires native Prometheus workspace ARNs.",
        },
        {
            "condition": Expr(
                'alltrue([for workspace in values(var.prometheus_workspaces) : try(split(":", workspace.arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", workspace.arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and connected Prometheus workspaces must use the same partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for workspace in values(var.prometheus_workspaces) : workspace.region == try(split(":", workspace.arn)[3], "") && trimsuffix(workspace.endpoint, "/") == try("https://aps-workspaces.${workspace.region}.${data.aws_partition.grafana_sources.dns_suffix}/workspaces/${split("/", workspace.arn)[1]}", "")])'
            ),
            "error_message": "Prometheus endpoints and signing Regions must match their native workspace identities.",
        },
    ]


def prometheus_data_sources_expression() -> Expr:
    return Expr("""{
    for name, workspace in var.prometheus_workspaces : name => {
      name = name
      uid = "amp-${substr(sha256(workspace.arn), 0, 16)}"
      type = "grafana-amazonprometheus-datasource"
      access = "proxy"
      url = workspace.endpoint
      jsonData = {
        httpMethod = "POST"
        sigV4Auth = true
        sigV4AuthType = "default"
        sigV4Region = workspace.region
        sigv4Service = "aps"
      }
    }
  }""")
