"""Workflow-owned delivery permissions compose with existing task policy dependencies."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.step_functions_logs import ROLE_ARN_PATTERN

DELIVERY_ACTIONS = (
    "logs:CreateLogDelivery",
    "logs:GetLogDelivery",
    "logs:UpdateLogDelivery",
    "logs:DeleteLogDelivery",
    "logs:ListLogDeliveries",
    "logs:PutResourcePolicy",
    "logs:DescribeResourcePolicies",
    "logs:DescribeLogGroups",
)


def workflow_log_destination() -> Expr:
    return Expr('"${trimsuffix(var.workflow_logs.arn, ":*")}:*"')


def workflow_log_role_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                f'can(regex("{ROLE_ARN_PATTERN}", var.role_arn)) && try(split(":", var.role_arn)[1], "") == data.aws_partition.workflow_logs.partition && try(split(":", var.role_arn)[4], "") == data.aws_caller_identity.workflow_logs.account_id'
            ),
            "error_message": "Execution logging requires a valid external IAM role ARN in the deployment partition and account.",
        }
    ]


def workflow_log_preconditions() -> list[dict]:
    return [
        *workflow_log_role_preconditions(),
        {
            "condition": Expr(
                'can(regex("^arn:[^:]+:logs:[^:]+:[0-9]{12}:log-group:[A-Za-z0-9_./#-]+$", trimsuffix(var.workflow_logs.arn, ":*"))) && length("${trimsuffix(var.workflow_logs.arn, ":*")}:*") <= 256'
            ),
            "error_message": "Workflow logging requires a native log-group ARN with a delivery ARN of at most 256 characters.",
        },
        {
            "condition": Expr(
                'try(split(":", var.workflow_logs.arn)[1], "") == data.aws_partition.workflow_logs.partition && try(split(":", var.workflow_logs.arn)[3], "") == data.aws_region.workflow_logs.region && try(split(":", var.workflow_logs.arn)[4], "") == data.aws_caller_identity.workflow_logs.account_id'
            ),
            "error_message": "Workflow and log group must share the deployment partition, Region, and account.",
        },
        {
            "condition": Expr(
                'contains(["STANDARD", "INFREQUENT_ACCESS"], var.workflow_logs.log_group_class) && contains(["STANDARD", "EXPRESS"], var.state_machine_type) && contains(["ALL", "ERROR", "FATAL"], var.workflow_logs.level)'
            ),
            "error_message": "Execution logging requires a Standard or Express workflow, a Standard or Infrequent Access group, and an enabled log level.",
        },
    ]


def workflow_log_policy_preconditions() -> list[dict]:
    return [
        *workflow_log_role_preconditions(),
        {
            "condition": Expr("data.aws_iam_role.workflow_logs.arn == var.role_arn"),
            "error_message": "The resolved execution role ARN must exactly match the configured role, including its path.",
        },
    ]


def add_workflow_log_attributes(attrs: dict) -> None:
    attrs["logging_configuration"] = {
        "log_destination": workflow_log_destination(),
        "level": Expr("var.workflow_logs.level"),
        "include_execution_data": Expr("var.workflow_logs.include_execution_data"),
    }
    dependencies = str(attrs.get("depends_on", "[]"))[1:-1]
    attrs["depends_on"] = Expr(
        f"[{dependencies}{', ' if dependencies else ''}aws_iam_role_policy.workflow_logs]"
    )
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + workflow_log_preconditions()


def render_workflow_logs(renderer: HCLRenderer) -> str:
    content = 'data "aws_partition" "workflow_logs" {}\ndata "aws_region" "workflow_logs" {}\ndata "aws_caller_identity" "workflow_logs" {}\n\ndata "aws_iam_role" "workflow_logs" {\n  name = element(reverse(split("/", var.role_arn)), 0)\n}\n\n'
    return content + renderer.render_resource(
        "aws_iam_role_policy",
        "workflow_logs",
        {
            "name_prefix": "execution-logs-",
            "role": Expr("data.aws_iam_role.workflow_logs.name"),
            "policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": list(DELIVERY_ACTIONS),
                            "Resource": "*",
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                            "Resource": Expr(
                                '"${trimsuffix(var.workflow_logs.arn, ":*")}:log-stream:*"'
                            ),
                        },
                    ],
                },
                depth=2,
            ),
            "lifecycle": {"precondition": workflow_log_policy_preconditions()},
        },
    )
