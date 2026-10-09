"""Native service selectors and cluster-scoped permissions stop discovered ECS tasks."""

import json

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.fis import ACTION_NAME_PATTERN, SELECTION_MODES
from app.models.iam_role import ROLE_ARN_PATTERN


def ecs_fault_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                f'can(regex("{ROLE_ARN_PATTERN}", var.role_arn)) && try(split(":", var.role_arn)[1], "") == data.aws_partition.experiment.partition && try(split(":", var.role_arn)[4], "") == data.aws_caller_identity.experiment.account_id'
            ),
            "error_message": "ECS experiments require an external IAM role in the deployment partition and account.",
        },
        {
            "condition": Expr(
                'can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:cluster/[A-Za-z0-9_-]{1,255}$", var.fis_ecs_service.cluster_arn)) && try(split(":", var.fis_ecs_service.cluster_arn)[1], "") == data.aws_partition.experiment.partition && try(split(":", var.fis_ecs_service.cluster_arn)[3], "") == data.aws_region.experiment.region && try(split(":", var.fis_ecs_service.cluster_arn)[4], "") == data.aws_caller_identity.experiment.account_id'
            ),
            "error_message": "ECS targets require a native cluster ARN in the deployment partition, Region, and account.",
        },
        {
            "condition": Expr(
                'can(regex("^[A-Za-z0-9_-]{1,255}$", var.fis_ecs_service.cluster_name)) && var.fis_ecs_service.cluster_arn == format("arn:%s:ecs:%s:%s:cluster/%s", data.aws_partition.experiment.partition, data.aws_region.experiment.region, data.aws_caller_identity.experiment.account_id, var.fis_ecs_service.cluster_name)'
            ),
            "error_message": "The native ECS cluster name and ARN must identify the same cluster.",
        },
        {
            "condition": Expr(
                'can(regex("^[A-Za-z0-9_-]{1,255}$", var.fis_ecs_service.service_name)) && var.fis_ecs_service.service_arn == format("%s/%s", replace(var.fis_ecs_service.cluster_arn, ":cluster/", ":service/"), var.fis_ecs_service.service_name)'
            ),
            "error_message": "The native ECS service name and long ARN must identify a service in the connected cluster.",
        },
        {
            "condition": Expr(
                f"contains({json.dumps(SELECTION_MODES)}, var.fis_ecs_selection)"
            ),
            "error_message": "Running task selection must be ALL or COUNT(1) through COUNT(5).",
        },
        {
            "condition": Expr(f'can(regex("{ACTION_NAME_PATTERN}", var.action_name))'),
            "error_message": "Experiment action names require 1–64 letters, numbers, underscores, or hyphens.",
        },
    ]


def add_ecs_fault_attributes(attrs: dict, renderer: HCLRenderer) -> None:
    attrs["action"] = {
        "name": Expr("var.action_name"),
        "action_id": "aws:ecs:stop-task",
        "target": {"key": "Tasks", "value": "managed_ecs"},
    }
    attrs["target"] = {
        "name": "managed_ecs",
        "resource_type": "aws:ecs:task",
        "parameters": Expr(
            renderer.render_expression(
                {
                    "cluster": Expr("var.fis_ecs_service.cluster_name"),
                    "service": Expr("var.fis_ecs_service.service_name"),
                },
                depth=3,
            )
        ),
        "filter": {"path": "LastStatus", "values": ["RUNNING"]},
        "selection_mode": Expr("var.fis_ecs_selection"),
    }
    attrs["depends_on"] = Expr("[aws_iam_role_policy.fis_ecs]")
    attrs["lifecycle"] = {"precondition": ecs_fault_preconditions()}


def render_ecs_fault_policy(renderer: HCLRenderer) -> str:
    content = 'data "aws_iam_role" "fis_ecs" {\n  name = element(reverse(split("/", var.role_arn)), 0)\n}\n\nlocals {\n  fis_ecs_task_arn = format("%s/*", replace(var.fis_ecs_service.cluster_arn, ":cluster/", ":task/"))\n}\n\n'
    cluster_condition = {
        "ArnEquals": {"ecs:cluster": Expr("var.fis_ecs_service.cluster_arn")},
        "StringEquals": {
            "aws:RequestedRegion": Expr("data.aws_region.experiment.region")
        },
    }
    return content + renderer.render_resource(
        "aws_iam_role_policy",
        "fis_ecs",
        {
            "name_prefix": "fis-ecs-",
            "role": Expr("data.aws_iam_role.fis_ecs.name"),
            "policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["ecs:DescribeTasks", "ecs:StopTask"],
                            "Resource": Expr("local.fis_ecs_task_arn"),
                            "Condition": cluster_condition,
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["ecs:ListTasks"],
                            "Resource": "*",
                            "Condition": cluster_condition,
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["tag:GetResources"],
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
                    *ecs_fault_preconditions(),
                    {
                        "condition": Expr(
                            "data.aws_iam_role.fis_ecs.arn == var.role_arn"
                        ),
                        "error_message": "The resolved experiment role ARN must exactly match the configured role, including its path.",
                    },
                ]
            },
        },
    )
