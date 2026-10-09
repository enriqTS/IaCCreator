"""Explicit EC2 fault templates and their policies share native scope guards."""

import json

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.fis import ACTION_NAME_PATTERN, SELECTION_MODES
from app.models.iam_role import ROLE_ARN_PATTERN


def ec2_fault_preconditions() -> list[dict]:
    selections = json.dumps(SELECTION_MODES)
    return [
        {
            "condition": Expr(
                f'can(regex("{ROLE_ARN_PATTERN}", var.role_arn)) && try(split(":", var.role_arn)[1], "") == data.aws_partition.experiment.partition && try(split(":", var.role_arn)[4], "") == data.aws_caller_identity.experiment.account_id'
            ),
            "error_message": "EC2 experiments require an external IAM role in the deployment partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for instance in values(var.fis_ec2_targets) : can(regex("^arn:[^:]+:ec2:[^:]+:[0-9]{12}:instance/i-([a-f0-9]{8}|[a-f0-9]{17})$", instance.arn)) && try(split(":", instance.arn)[1], "") == data.aws_partition.experiment.partition && try(split(":", instance.arn)[3], "") == data.aws_region.experiment.region && try(split(":", instance.arn)[4], "") == data.aws_caller_identity.experiment.account_id])'
            ),
            "error_message": "Explicit EC2 targets must use native instance ARNs in the deployment partition, Region, and account.",
        },
        {
            "condition": Expr(
                "length(var.fis_ec2_targets) >= 1 && length(var.fis_ec2_targets) <= 5 && length(distinct(local.fis_ec2_arns)) == length(var.fis_ec2_targets)"
            ),
            "error_message": "An EC2 experiment requires one to five distinct native instance targets.",
        },
        {
            "condition": Expr(
                f'contains({selections}, var.fis_ec2_action.selection_mode) && (var.fis_ec2_action.selection_mode == "ALL" || try(tonumber(regex("^COUNT[(]([1-5])[)]$", var.fis_ec2_action.selection_mode)[0]), 6) <= length(var.fis_ec2_targets))'
            ),
            "error_message": "Selection must be ALL or a count from one through the connected instance count.",
        },
        {
            "condition": Expr(
                'contains(["reboot", "stop"], var.fis_ec2_action.operation) && (var.fis_ec2_action.operation != "stop" || alltrue([for instance in values(var.fis_ec2_targets) : instance.can_stop]))'
            ),
            "error_message": "EC2 experiments support reboot or stop; stopping requires EBS-backed roots without stop protection.",
        },
        {
            "condition": Expr(f'can(regex("{ACTION_NAME_PATTERN}", var.action_name))'),
            "error_message": "Experiment action names require 1–64 letters, numbers, underscores, or hyphens.",
        },
    ]


def add_ec2_fault_attributes(attrs: dict) -> None:
    attrs["action"] = {
        "name": Expr("var.action_name"),
        "action_id": Expr('"aws:ec2:${var.fis_ec2_action.operation}-instances"'),
        "target": {"key": "Instances", "value": "managed_ec2"},
    }
    attrs["target"] = {
        "name": "managed_ec2",
        "resource_type": "aws:ec2:instance",
        "resource_arns": Expr("local.fis_ec2_arns"),
        "selection_mode": Expr("var.fis_ec2_action.selection_mode"),
    }
    attrs["depends_on"] = Expr("[aws_iam_role_policy.fis_ec2]")
    attrs["lifecycle"] = {"precondition": ec2_fault_preconditions()}


def render_ec2_fault_policy(renderer: HCLRenderer) -> str:
    content = 'data "aws_iam_role" "fis_ec2" {\n  name = element(reverse(split("/", var.role_arn)), 0)\n}\n\nlocals {\n  fis_ec2_arns = [for instance in values(var.fis_ec2_targets) : instance.arn]\n}\n\n'
    return content + renderer.render_resource(
        "aws_iam_role_policy",
        "fis_ec2",
        {
            "name_prefix": "fis-ec2-",
            "role": Expr("data.aws_iam_role.fis_ec2.name"),
            "policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": Expr(
                                'var.fis_ec2_action.operation == "stop" ? ["ec2:StopInstances", "ec2:StartInstances"] : ["ec2:RebootInstances"]'
                            ),
                            "Resource": Expr("local.fis_ec2_arns"),
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["ec2:DescribeInstances"],
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
                    *ec2_fault_preconditions(),
                    {
                        "condition": Expr(
                            "data.aws_iam_role.fis_ec2.arn == var.role_arn"
                        ),
                        "error_message": "The resolved experiment role ARN must exactly match the configured role, including its path.",
                    },
                ]
            },
        },
    )
