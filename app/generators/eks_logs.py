"""Input-only naming lets the log group exist before EKS logging is enabled."""

import json

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eks_logs import LOG_TYPES


def eks_log_preconditions() -> list[dict]:
    allowed = json.dumps(LOG_TYPES)
    return [
        {
            "condition": Expr(
                'can(regex("^[0-9A-Za-z][A-Za-z0-9_-]{0,99}$", var.cluster_name))'
            ),
            "error_message": "Control-plane logging requires a valid EKS cluster name of 1–100 characters.",
        },
        {
            "condition": Expr(
                'trimsuffix(var.control_plane_log_group.arn, ":*") == "arn:${data.aws_partition.eks_logs.partition}:logs:${data.aws_region.eks_logs.region}:${data.aws_caller_identity.eks_logs.account_id}:log-group:/aws/eks/${var.cluster_name}/cluster"'
            ),
            "error_message": "EKS requires its native /aws/eks/<cluster-name>/cluster log group in the same partition, Region, and account.",
        },
        {
            "condition": Expr(
                'var.control_plane_log_group.log_group_class == "STANDARD" && var.control_plane_log_group.kms_key_arn == ""'
            ),
            "error_message": "Managed EKS control-plane logging currently supports Standard groups with default encryption; customer-managed keys require separate service-linked-role key-policy support.",
        },
        {
            "condition": Expr(
                f"length(var.enabled_cluster_log_types) > 0 && length(distinct(var.enabled_cluster_log_types)) == length(var.enabled_cluster_log_types) && alltrue([for name in var.enabled_cluster_log_types : contains({allowed}, name)])"
            ),
            "error_message": "Select at least one unique native EKS control-plane log type.",
        },
    ]


def add_eks_log_attributes(attrs: dict) -> None:
    attrs["enabled_cluster_log_types"] = Expr("var.enabled_cluster_log_types")
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + eks_log_preconditions()


def render_eks_log_resources() -> str:
    return 'data "aws_partition" "eks_logs" {}\ndata "aws_region" "eks_logs" {}\ndata "aws_caller_identity" "eks_logs" {}\n'
