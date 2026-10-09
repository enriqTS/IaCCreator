"""Pod selectors share native cluster and authentication guards with role policies."""

import json

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.fis import ACTION_NAME_PATTERN, SELECTION_MODES
from app.models.connection_configs.fis_eks import (
    KUBERNETES_NAME_PATTERN,
    SYSTEM_NAMESPACES,
)
from app.models.iam_role import ROLE_ARN_PATTERN


def eks_version_condition(version: str) -> Expr:
    return Expr(
        f'can(regex("^[0-9]+[.][0-9]+$", {version})) && try(tonumber(split(".", {version})[0]) > 1 || (tonumber(split(".", {version})[0]) == 1 && tonumber(split(".", {version})[1]) >= 30), false)'
    )


def eks_fault_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                f'can(regex("{ROLE_ARN_PATTERN}", var.role_arn)) && try(split(":", var.role_arn)[1], "") == data.aws_partition.experiment.partition && try(split(":", var.role_arn)[4], "") == data.aws_caller_identity.experiment.account_id'
            ),
            "error_message": "EKS experiments require an external IAM role in the deployment partition and account.",
        },
        {
            "condition": Expr(
                'can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$", var.fis_eks_cluster.name)) && var.fis_eks_cluster.arn == format("arn:%s:eks:%s:%s:cluster/%s", data.aws_partition.experiment.partition, data.aws_region.experiment.region, data.aws_caller_identity.experiment.account_id, var.fis_eks_cluster.name)'
            ),
            "error_message": "EKS targets require matching native cluster name and ARN in the deployment partition, Region, and account.",
        },
        {
            "condition": Expr(
                f'contains(["API", "API_AND_CONFIG_MAP"], var.fis_eks_cluster.authentication_mode) && ({eks_version_condition("var.fis_eks_cluster.version")})'
            ),
            "error_message": "FIS pod actions require EKS API authentication and Kubernetes 1.30 or newer.",
        },
        {
            "condition": Expr(
                f'can(regex("{KUBERNETES_NAME_PATTERN}", var.fis_eks_pods.namespace)) && !contains({json.dumps(SYSTEM_NAMESPACES)}, var.fis_eks_pods.namespace) && can(regex("{KUBERNETES_NAME_PATTERN}", var.fis_eks_pods.deployment_name))'
            ),
            "error_message": "Pod targets require explicit bounded deployment and non-system namespace names.",
        },
        {
            "condition": Expr(
                'can(regex("^iacc-fis-[0-9a-f]{12}$", var.fis_eks_pods.service_account)) && var.fis_eks_pods.kubernetes_group == format("iacc-fis-%s", substr(sha256(var.role_arn), 0, 12)) && contains(var.fis_eks_cluster.authorized_roles, var.role_arn)'
            ),
            "error_message": "Pod actions require a generated service account and the connected principal's ready EKS access entry.",
        },
        {
            "condition": Expr(
                f'contains({json.dumps(SELECTION_MODES)}, var.fis_eks_pods.selection_mode) && can(regex("{ACTION_NAME_PATTERN}", var.action_name))'
            ),
            "error_message": "Pod selection must be ALL or COUNT(1) through COUNT(5), with a bounded experiment action name.",
        },
    ]


def add_eks_fault_attributes(attrs: dict, renderer: HCLRenderer) -> None:
    attrs["action"] = {
        "name": Expr("var.action_name"),
        "action_id": "aws:eks:pod-delete",
        "parameter": {
            "key": "kubernetesServiceAccount",
            "value": Expr("var.fis_eks_pods.service_account"),
        },
        "target": {"key": "Pods", "value": "managed_eks"},
    }
    attrs["target"] = {
        "name": "managed_eks",
        "resource_type": "aws:eks:pod",
        "parameters": Expr(
            renderer.render_expression(
                {
                    "clusterIdentifier": Expr("var.fis_eks_cluster.arn"),
                    "namespace": Expr("var.fis_eks_pods.namespace"),
                    "selectorType": "deploymentName",
                    "selectorValue": Expr("var.fis_eks_pods.deployment_name"),
                },
                depth=3,
            )
        ),
        "selection_mode": Expr("var.fis_eks_pods.selection_mode"),
    }
    attrs["depends_on"] = Expr("[aws_iam_role_policy.fis_eks]")
    attrs["lifecycle"] = {"precondition": eks_fault_preconditions()}


def render_eks_fault_policy(renderer: HCLRenderer) -> str:
    content = 'data "aws_iam_role" "fis_eks" {\n  name = element(reverse(split("/", var.role_arn)), 0)\n}\n\n'
    return content + renderer.render_resource(
        "aws_iam_role_policy",
        "fis_eks",
        {
            "name_prefix": "fis-eks-",
            "role": Expr("data.aws_iam_role.fis_eks.name"),
            "policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["eks:DescribeCluster"],
                            "Resource": Expr("var.fis_eks_cluster.arn"),
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["ec2:DescribeSubnets", "tag:GetResources"],
                            "Resource": "*",
                            "Condition": {
                                "StringEquals": {
                                    "aws:RequestedRegion": Expr(
                                        "data.aws_region.experiment.region"
                                    )
                                }
                            },
                        },
                    ],
                },
                depth=2,
            ),
            "lifecycle": {
                "precondition": [
                    *eks_fault_preconditions(),
                    {
                        "condition": Expr(
                            "data.aws_iam_role.fis_eks.arn == var.role_arn"
                        ),
                        "error_message": "The resolved experiment role ARN must exactly match the configured role, including its path.",
                    },
                ]
            },
        },
    )
