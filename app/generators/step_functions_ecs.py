"""Synchronous ECS Fargate tasks merged into workflow definitions."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.workflow_states import PASS_STATE_FIELDS


def ecs_workflow_locals(
    bindings: dict[str, dict], has_lambda_tasks: bool, has_secret_tasks: bool
) -> str:
    renderer = HCLRenderer()
    binding_expression = renderer.render_expression(bindings)
    fields = renderer.render_expression(list(PASS_STATE_FIELDS))
    if has_lambda_tasks:
        source = "local.lambda_workflow_definition"
    elif has_secret_tasks:
        source = "local.secret_workflow_definition"
    else:
        source = "var.definition"
    return (
        'data "aws_partition" "ecs_tasks" {}\n'
        "locals {\n"
        f"  ecs_bindings = {binding_expression}\n"
        f"  ecs_source_workflow = jsondecode({source})\n"
        "  ecs_task_states = { for name, task in local.ecs_bindings : name => merge(\n"
        '    { for key, value in try(local.ecs_source_workflow.States[name], {}) : key => value if !contains(["Type", "Result"], key) },\n'
        '    { Type = "Task", Resource = "arn:${data.aws_partition.ecs_tasks.partition}:states:::ecs:runTask.sync", Parameters = { Cluster = task.cluster, TaskDefinition = task.definition, LaunchType = "FARGATE", Count = task.count, NetworkConfiguration = { AwsvpcConfiguration = { Subnets = task.subnets, SecurityGroups = task.security_groups, AssignPublicIp = task.assign_public_ip ? "ENABLED" : "DISABLED" } } } }\n'
        "  ) }\n"
        "  ecs_workflow_definition = jsonencode(merge(local.ecs_source_workflow, { States = merge(local.ecs_source_workflow.States, local.ecs_task_states) }))\n"
        "  ecs_tasks_valid = try(\n"
        '    try(local.ecs_source_workflow.QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        "    contains(keys(local.ecs_source_workflow.States), local.ecs_source_workflow.StartAt) &&\n"
        "    alltrue([for name, task in local.ecs_bindings :\n"
        '      local.ecs_source_workflow.States[name].Type == "Pass" &&\n'
        '      try(local.ecs_source_workflow.States[name].QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        f"      length(setsubtract(toset(keys(local.ecs_source_workflow.States[name])), toset({fields}))) == 0 &&\n"
        "      length(task.subnets) > 0 && task.count >= 1 && task.count <= 10 &&\n"
        "      (\n"
        '        (try(local.ecs_source_workflow.States[name].End, false) == true && !contains(keys(local.ecs_source_workflow.States[name]), "Next")) ||\n'
        '        (!contains(keys(local.ecs_source_workflow.States[name]), "End") && contains(keys(local.ecs_source_workflow.States), try(local.ecs_source_workflow.States[name].Next, "")))\n'
        "      )\n"
        "    ]), false\n"
        "  )\n"
        "}\n"
    )


def ecs_workflow_attributes(has_lambda_tasks: bool, has_secret_tasks: bool) -> dict:
    dependencies = ["aws_iam_role_policy.ecs_tasks"]
    preconditions = [
        {
            "condition": Expr("local.ecs_tasks_valid"),
            "error_message": "ECS task bindings require top-level JSONPath Pass states, valid transitions, and task subnets.",
        }
    ]
    if has_lambda_tasks:
        dependencies.append("aws_iam_role_policy.lambda_tasks")
        preconditions.append(
            {
                "condition": Expr("local.lambda_tasks_valid"),
                "error_message": "Lambda task bindings require top-level JSONPath Pass states with valid transitions and supported fields.",
            }
        )
    if has_secret_tasks:
        dependencies.append("aws_iam_role_policy.runtime_secrets")
        preconditions.append(
            {
                "condition": Expr("local.secret_tasks_valid"),
                "error_message": "Secret task bindings require top-level JSONPath Pass states with valid transitions and supported fields.",
            }
        )
    return {
        "definition": Expr("local.ecs_workflow_definition"),
        "depends_on": Expr(f"[{', '.join(dependencies)}]"),
        "lifecycle": {"precondition": preconditions},
    }
