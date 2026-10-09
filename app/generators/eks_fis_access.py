"""Cluster-owned access entries consume role lookups without depending on templates."""

from app.generators.fis_eks import eks_version_condition
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.iam_role import ROLE_ARN_PATTERN


def access_preconditions(cluster: str) -> list[dict]:
    return [
        {
            "condition": Expr(
                f'can(regex("{ROLE_ARN_PATTERN}", each.value.arn)) && each.value.arn == each.value.native_arn && alltrue([for index in [1, 4] : try(split(":", each.value.arn)[index], "") == split(":", {cluster}.arn)[index]])'
            ),
            "error_message": "EKS experiment access requires the exact native role ARN in the cluster account and partition.",
        },
        {
            "condition": Expr(
                f'try(contains(["API", "API_AND_CONFIG_MAP"], {cluster}.access_config[0].authentication_mode), false) && ({eks_version_condition(f"{cluster}.version")})'
            ),
            "error_message": "Experiment access requires EKS API authentication and Kubernetes 1.30 or newer.",
        },
    ]


def render_experiment_access(name: str, renderer: HCLRenderer) -> str:
    cluster = f"aws_eks_cluster.{name}"
    return renderer.render_resource(
        "aws_eks_access_entry",
        "fis_experiments",
        {
            "for_each": Expr("var.fis_experiment_roles"),
            "cluster_name": Expr(f"{cluster}.name"),
            "principal_arn": Expr("each.value.arn"),
            "type": "STANDARD",
            "kubernetes_groups": [
                Expr('format("iacc-fis-%s", substr(sha256(each.value.arn), 0, 12))')
            ],
            "lifecycle": {"precondition": access_preconditions(cluster)},
        },
    )
