"""Shared ADOT sidecar resources and capacity guards."""

from app.generators.hcl_renderer import Expr, HCLRenderer

COLLECTOR_IMAGE = "public.ecr.aws/aws-observability/aws-otel-collector:v0.49.0"
COLLECTOR_CPU = 64
COLLECTOR_MEMORY = 256


def collector_capacity_precondition(cpu: int, memory: int) -> dict:
    return {
        "condition": Expr(
            f"try(tonumber(var.ecs_cpu), 0) >= {cpu} + sum(concat([0], [for container in jsondecode(var.container_definitions) : try(container.cpu, 0)])) && try(tonumber(var.ecs_memory), 0) >= {memory} + sum(concat([0], [for container in jsondecode(var.container_definitions) : max(try(container.memory, 0), try(container.memoryReservation, 0))]))"
        ),
        "error_message": f"Task capacity must cover application reservations plus {cpu} CPU units and {memory} MiB for collection.",
    }


def sidecar_expression(
    renderer: HCLRenderer,
    *,
    name: str,
    configuration: str,
    log_group: str,
    region: str,
) -> str:
    return renderer.render_expression(
        {
            "name": name,
            "image": COLLECTOR_IMAGE,
            "essential": False,
            "cpu": COLLECTOR_CPU,
            "memory": COLLECTOR_MEMORY,
            "command": ["--config=env:AOT_CONFIG_CONTENT"],
            "environment": [
                {"name": "AOT_CONFIG_CONTENT", "value": Expr(configuration)},
                {"name": "AWS_REGION", "value": Expr(region)},
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": Expr(log_group),
                    "awslogs-region": Expr(region),
                    "awslogs-stream-prefix": "collector",
                },
            },
        }
    )
