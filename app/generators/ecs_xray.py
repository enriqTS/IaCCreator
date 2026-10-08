"""Task-local OTLP collection stamps native membership and uses task credentials."""

from app.generators.ecs_collector import (
    COLLECTOR_CPU,
    COLLECTOR_MEMORY,
    collector_capacity_precondition,
    sidecar_expression,
)
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.xray_ecs_filters import ECS_CLUSTER_ANNOTATION
from app.generators.xray_upload import render_xray_upload_policy

COLLECTOR_NAME = "iac-xray-collector"
OTLP_PORTS = [4317, 4318]
TRACE_ENVIRONMENT = {
    "OTEL_TRACES_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://127.0.0.1:4318/v1/traces",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/protobuf",
}


def xray_configuration_expression(name: str) -> Expr:
    return Expr(f'''yamlencode({{
    receivers = {{ otlp = {{ protocols = {{
      grpc = {{ endpoint = "127.0.0.1:4317" }}
      http = {{ endpoint = "127.0.0.1:4318" }}
    }} }} }}
    processors = {{
      memory_limiter = {{ check_interval = "1s", limit_mib = 192, spike_limit_mib = 48 }}
      resource_detection = {{ detectors = ["ecs"], timeout = "2s", override = false }}
      "attributes/xray_identity" = {{ actions = [{{
        key = "{ECS_CLUSTER_ANNOTATION}"
        value = aws_ecs_cluster.{name}.arn
        action = "upsert"
      }}] }}
      batch = {{ timeout = "1s", send_batch_size = 50 }}
    }}
    exporters = {{ awsxray = {{
      region = data.aws_region.ecs_xray.region
      local_mode = true
      indexed_attributes = ["{ECS_CLUSTER_ANNOTATION}"]
      index_all_attributes = false
      telemetry = {{ enabled = false }}
    }} }}
    service = {{ pipelines = {{ traces = {{
      receivers = ["otlp"]
      processors = ["memory_limiter", "resource_detection", "attributes/xray_identity", "batch"]
      exporters = ["awsxray"]
    }} }} }}
  }})''')


def xray_task_preconditions(
    *, prometheus: bool, applications: str = "var.container_definitions"
) -> list[dict]:
    keys = HCLRenderer().render_expression(list(TRACE_ENVIRONMENT))
    guards = [
        {
            "condition": Expr(
                f'length(jsondecode(var.container_definitions)) > 0 && alltrue([for container in jsondecode(var.container_definitions) : container.name != "{COLLECTOR_NAME}"])'
            ),
            "error_message": f"Provide application containers without the reserved {COLLECTOR_NAME} name.",
        },
        collector_capacity_precondition(
            COLLECTOR_CPU * (2 if prometheus else 1),
            COLLECTOR_MEMORY * (2 if prometheus else 1),
        ),
        {
            "condition": Expr(
                'var.ecs_launch_type == "FARGATE" && length(var.subnet_ids) > 0 && length(var.security_group_ids) > 0'
            ),
            "error_message": "Tracing requires Linux Fargate tasks with subnet and security-group placement.",
        },
        {
            "condition": Expr(
                'alltrue(flatten([for container in jsondecode(var.container_definitions) : [for mapping in try(container.portMappings, []) : try(mapping.protocol, "tcp") == "udp" || (!contains([4317, 4318], try(mapping.containerPort, 0)) && alltrue([for port in [4317, 4318] : try(port < tonumber(split("-", mapping.containerPortRange)[0]) || port > tonumber(split("-", mapping.containerPortRange)[1]), true)]))]]))'
            ),
            "error_message": "Application TCP port mappings must not reserve OTLP collector ports 4317 or 4318.",
        },
        {
            "condition": Expr(
                f"alltrue(flatten([for container in jsondecode({applications}) : [for secret in try(container.secrets, []) : !contains({keys}, secret.name)]]))"
            ),
            "error_message": "Application secrets must not override connection-owned OTLP tracing environment variables.",
        },
    ]
    if prometheus:
        guards.append(
            {
                "condition": Expr(
                    "!contains([4317, 4318], var.prometheus_collection.application_metrics_port)"
                ),
                "error_message": "Prometheus application scraping must not use the OTLP collector ports.",
            }
        )
    return guards


def add_xray_task_attributes(
    attrs: dict, name: str, renderer: HCLRenderer, *, prometheus: bool
) -> None:
    containers = attrs["container_definitions"]
    keys = renderer.render_expression(list(TRACE_ENVIRONMENT))
    environment = renderer.render_expression(
        [{"name": key, "value": value} for key, value in TRACE_ENVIRONMENT.items()]
    )
    applications = f"[for container in jsondecode({containers}) : merge(container, {{ environment = concat([for item in try(container.environment, []) : item if !contains({keys}, item.name)], {environment}) }})]"
    collector = sidecar_expression(
        renderer,
        name=COLLECTOR_NAME,
        configuration="local.xray_collector_configuration",
        log_group=f"aws_cloudwatch_log_group.{name}_xray.name",
        region="data.aws_region.ecs_xray.region",
    )
    attrs["container_definitions"] = Expr(
        f"jsonencode(concat({applications}, [{collector}]))"
    )
    attrs["execution_role_arn"] = Expr(f"aws_iam_role.{name}_role.arn")
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + xray_task_preconditions(prometheus=prometheus, applications=str(containers))


def render_xray_collection_resources(name: str, renderer: HCLRenderer) -> str:
    return (
        'data "aws_region" "ecs_xray" {}\n\n'
        + "locals {\n  xray_collector_configuration = "
        + xray_configuration_expression(name)
        + "\n}\n\n"
        + renderer.render_resource(
            "aws_cloudwatch_log_group",
            f"{name}_xray",
            {"name": f"/aws/ecs/{name}/xray", "retention_in_days": 30},
        )
        + "\n"
        + render_xray_upload_policy(
            name, renderer, "data.aws_region.ecs_xray.region", telemetry=False
        )
    )
