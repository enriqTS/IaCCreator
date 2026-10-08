"""Collector-stamped cluster annotations select ECS trace membership."""

from app.generators.hcl_renderer import Expr
from app.generators.xray_filters import group_configuration_preconditions

ECS_CLUSTER_ANNOTATION = "iac_ecs_cluster_arn"


def ecs_group_selectors() -> Expr:
    return Expr(
        f'[for cluster in values(var.xray_ecs_clusters) : format("annotation.{ECS_CLUSTER_ANNOTATION} = %s", jsonencode(cluster.arn))]'
    )


def ecs_group_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.xray_ecs_clusters) > 0 && alltrue([for cluster in values(var.xray_ecs_clusters) : can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:cluster/[A-Za-z0-9_-]{1,255}$", cluster.arn)) && cluster.name == try(split("/", cluster.arn)[1], "")])'
            ),
            "error_message": "X-Ray group members require native ECS cluster identities.",
        },
        {
            "condition": Expr(
                'alltrue([for cluster in values(var.xray_ecs_clusters) : try(split(":", cluster.arn)[1], "") == data.aws_partition.xray_tracing.partition && try(split(":", cluster.arn)[3], "") == data.aws_region.xray_tracing.region && try(split(":", cluster.arn)[4], "") == data.aws_caller_identity.xray_tracing.account_id])'
            ),
            "error_message": "ECS clusters and their X-Ray group must share a partition, Region, and account.",
        },
        *group_configuration_preconditions(),
    ]
