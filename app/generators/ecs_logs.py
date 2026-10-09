"""Compose application awslogs settings before connection-owned collectors."""

from app.generators.ecs_collector import COLLECTOR_MEMORY
from app.generators.ecs_prometheus import COLLECTOR_NAME as PROMETHEUS_COLLECTOR
from app.generators.ecs_xray import COLLECTOR_NAME as XRAY_COLLECTOR
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.ecs_logs import (
    CONTAINER_NAME_PATTERN,
    STREAM_PREFIX_PATTERN,
)

RESERVED_CONTAINERS = (PROMETHEUS_COLLECTOR, XRAY_COLLECTOR)


def ecs_log_preconditions(collector_count: int) -> list[dict]:
    reserved = HCLRenderer().render_expression(list(RESERVED_CONTAINERS))
    return [
        {
            "condition": Expr(
                "length(var.ecs_logs) > 0 && length(distinct([for container in jsondecode(var.container_definitions) : container.name])) == length(jsondecode(var.container_definitions)) && alltrue([for name in keys(var.ecs_logs) : contains([for container in jsondecode(var.container_definitions) : container.name], name)])"
            ),
            "error_message": "Managed logs require uniquely named application containers and every selected container in container_definitions.",
        },
        {
            "condition": Expr(
                "alltrue([for container in jsondecode(var.container_definitions) : try(container.logConfiguration, null) == null || try(length(keys(container.logConfiguration)) == 0, false) if contains(keys(var.ecs_logs), container.name)])"
            ),
            "error_message": "Remove manually configured logging from each selected application container before adding a managed log connection.",
        },
        {
            "condition": Expr(
                'alltrue([for binding in values(var.ecs_logs) : can(regex("^arn:[^:]+:logs:[^:]+:[0-9]{12}:log-group:[A-Za-z0-9_./#-]+$", trimsuffix(binding.arn, ":*")))])'
            ),
            "error_message": "Application logging requires native CloudWatch log-group ARNs.",
        },
        {
            "condition": Expr(
                'alltrue([for binding in values(var.ecs_logs) : try(split(":", binding.arn)[1], "") == data.aws_partition.ecs_logs.partition && try(split(":", binding.arn)[3], "") == data.aws_region.ecs_logs.region && try(split(":", binding.arn)[4], "") == data.aws_caller_identity.ecs_logs.account_id])'
            ),
            "error_message": "ECS tasks and managed log groups must share a partition, Region, and account.",
        },
        {
            "condition": Expr(
                f'alltrue([for name, binding in var.ecs_logs : can(regex("{CONTAINER_NAME_PATTERN}", name)) && !contains({reserved}, name) && can(regex("{STREAM_PREFIX_PATTERN}", binding.stream_prefix)) && contains(["non-blocking", "blocking"], binding.mode) && floor(binding.buffer_size_mib) == binding.buffer_size_mib && (binding.mode == "blocking" ? binding.buffer_size_mib == 0 : binding.buffer_size_mib >= 1 && binding.buffer_size_mib <= 64)])'
            ),
            "error_message": "Managed logs require application container names, a bounded stream prefix, and a valid delivery mode with a 1–64 MiB non-blocking buffer (zero for blocking).",
        },
        {
            "condition": Expr(
                'var.ecs_launch_type == "FARGATE" && length(var.subnet_ids) > 0 && length(var.security_group_ids) > 0'
            ),
            "error_message": "Application logging requires the modeled Linux Fargate task and subnet/security-group placement.",
        },
        {
            "condition": Expr(
                f'try(tonumber(var.ecs_memory), 0) >= {collector_count * COLLECTOR_MEMORY} + sum(concat([0], [for container in jsondecode(var.container_definitions) : max(try(container.memory, 0), try(container.memoryReservation, 0))])) + sum(concat([0], [for binding in values(var.ecs_logs) : binding.buffer_size_mib if binding.mode == "non-blocking"]))'
            ),
            "error_message": "Task memory must cover application reservations, managed collector reservations, and non-blocking log buffers.",
        },
    ]


def add_ecs_log_attributes(attrs: dict, name: str, collector_count: int) -> None:
    containers = attrs["container_definitions"]
    attrs["container_definitions"] = Expr(
        f'jsonencode([for container in jsondecode({containers}) : merge(container, {{ for key, configuration in local.application_log_configurations : "logConfiguration" => configuration if key == container.name }})])'
    )
    attrs["execution_role_arn"] = Expr(f"aws_iam_role.{name}_role.arn")
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + ecs_log_preconditions(collector_count)


def render_ecs_log_resources() -> str:
    return """data "aws_partition" "ecs_logs" {}
data "aws_region" "ecs_logs" {}
data "aws_caller_identity" "ecs_logs" {}

locals {
  application_log_configurations = {
    for container, binding in var.ecs_logs : container => {
      logDriver = "awslogs"
      options = merge({
        awslogs-group = try(split(":", trimsuffix(binding.arn, ":*"))[6], "")
        awslogs-region = try(split(":", binding.arn)[3], "")
        awslogs-stream-prefix = binding.stream_prefix
        awslogs-create-group = "false"
        mode = binding.mode
      }, binding.mode == "non-blocking" ? { max-buffer-size = "${binding.buffer_size_mib}m" } : {})
    }
  }
}
"""
