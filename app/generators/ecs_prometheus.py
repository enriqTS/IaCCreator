"""ADOT sidecars share native task credentials and preserve application containers."""

from app.generators.ecs_collector import (
    COLLECTOR_CPU,
    COLLECTOR_MEMORY,
    collector_capacity_precondition,
    sidecar_expression,
)
from app.generators.ecs_collector import COLLECTOR_IMAGE as COLLECTOR_IMAGE
from app.generators.hcl_renderer import Expr, HCLRenderer

COLLECTOR_NAME = "iac-prometheus-collector"


def collector_configuration_expression() -> Expr:
    return Expr("""yamlencode({
    extensions = { sigv4auth = { region = data.aws_region.ecs_prometheus.region, service = "aps" } }
    receivers = merge(
      { awsecscontainermetrics = { collection_interval = "${var.prometheus_collection.collection_interval_seconds}s" } },
      var.prometheus_collection.application_metrics_port > 0 ? {
        prometheus = { config = {
          global = { scrape_interval = "${var.prometheus_collection.collection_interval_seconds}s", scrape_timeout = "10s" }
          scrape_configs = [{ job_name = "ecs-application", metrics_path = "/metrics", static_configs = [{ targets = ["127.0.0.1:${var.prometheus_collection.application_metrics_port}"] }] }]
        } }
      } : {}
    )
    processors = {
      memory_limiter = { check_interval = "1s", limit_mib = 192, spike_limit_mib = 48 }
      resource_detection = { detectors = ["ecs"], timeout = "2s", override = false }
      batch = { timeout = "${var.prometheus_collection.collection_interval_seconds}s", send_batch_size = 1024 }
    }
    exporters = {
      for name, workspace in var.prometheus_collection_workspaces : "prometheus_remote_write/${name}" => {
        endpoint = "${trimsuffix(workspace.endpoint, "/")}/api/v1/remote_write"
        auth = { authenticator = "sigv4auth" }
        resource_to_telemetry_conversion = { enabled = true }
      }
    }
    service = {
      extensions = ["sigv4auth"]
      pipelines = { metrics = {
        receivers = concat(["awsecscontainermetrics"], var.prometheus_collection.application_metrics_port > 0 ? ["prometheus"] : [])
        processors = ["memory_limiter", "resource_detection", "batch"]
        exporters = [for name in keys(var.prometheus_collection_workspaces) : "prometheus_remote_write/${name}"]
      } }
    }
  })""")


def collection_preconditions() -> list[dict]:
    interval = "var.prometheus_collection.collection_interval_seconds"
    port = "var.prometheus_collection.application_metrics_port"
    return [
        {
            "condition": Expr(
                'length(var.prometheus_collection_workspaces) > 0 && alltrue([for workspace in values(var.prometheus_collection_workspaces) : can(regex("^arn:[^:]+:aps:[^:]+:[0-9]{12}:workspace/ws-[0-9a-f-]+$", workspace.arn))])'
            ),
            "error_message": "Collection requires native Prometheus workspace ARNs.",
        },
        {
            "condition": Expr(
                'alltrue([for workspace in values(var.prometheus_collection_workspaces) : try(split(":", workspace.arn)[1], "") == data.aws_partition.ecs_prometheus.partition && try(split(":", workspace.arn)[4], "") == data.aws_caller_identity.ecs_prometheus.account_id && workspace.region == data.aws_region.ecs_prometheus.region && workspace.region == try(split(":", workspace.arn)[3], "")])'
            ),
            "error_message": "ECS collection and destinations must share their partition, account, and Region.",
        },
        {
            "condition": Expr(
                'alltrue([for workspace in values(var.prometheus_collection_workspaces) : trimsuffix(workspace.endpoint, "/") == try("https://aps-workspaces.${workspace.region}.${data.aws_partition.ecs_prometheus.dns_suffix}/workspaces/${split("/", workspace.arn)[1]}", "")])'
            ),
            "error_message": "Collection endpoints must match native workspace identities.",
        },
        {
            "condition": Expr(
                f"{interval} >= 10 && {interval} <= 3600 && floor({interval}) == {interval} && {port} >= 0 && {port} <= 65535 && floor({port}) == {port}"
            ),
            "error_message": "Collection requires whole-second intervals from 10–3600 and an integer application port from 0–65535.",
        },
        {
            "condition": Expr(
                f'length(jsondecode(var.container_definitions)) > 0 && alltrue([for container in jsondecode(var.container_definitions) : container.name != "{COLLECTOR_NAME}"])'
            ),
            "error_message": f"Provide application containers without the reserved {COLLECTOR_NAME} name.",
        },
        collector_capacity_precondition(COLLECTOR_CPU, COLLECTOR_MEMORY),
        {
            "condition": Expr(
                'var.ecs_launch_type == "FARGATE" && length(var.subnet_ids) > 0 && length(var.security_group_ids) > 0'
            ),
            "error_message": "Collection requires Linux Fargate tasks with subnet and security-group placement.",
        },
    ]


def collector_expression(name: str, renderer: HCLRenderer) -> str:
    return sidecar_expression(
        renderer,
        name=COLLECTOR_NAME,
        configuration="local.prometheus_collector_configuration",
        log_group=f"aws_cloudwatch_log_group.{name}_prometheus.name",
        region="data.aws_region.ecs_prometheus.region",
    )


def add_prometheus_task_attributes(
    attrs: dict, name: str, renderer: HCLRenderer
) -> None:
    containers = attrs["container_definitions"]
    attrs["container_definitions"] = Expr(
        f"jsonencode(concat(jsondecode({containers}), [{collector_expression(name, renderer)}]))"
    )
    attrs["execution_role_arn"] = Expr(f"aws_iam_role.{name}_role.arn")
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + collection_preconditions()


def render_collection_resources(name: str, renderer: HCLRenderer) -> str:
    content = 'data "aws_partition" "ecs_prometheus" {}\ndata "aws_region" "ecs_prometheus" {}\ndata "aws_caller_identity" "ecs_prometheus" {}\n\n'
    content += (
        "locals {\n  prometheus_collector_configuration = "
        + collector_configuration_expression()
        + "\n}\n\n"
    )
    return content + renderer.render_resource(
        "aws_cloudwatch_log_group",
        f"{name}_prometheus",
        {"name": f"/aws/ecs/{name}/prometheus", "retention_in_days": 30},
    )
