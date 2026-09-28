"""Synchronous Batch SubmitJob states merged into workflow definitions."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.workflow_states import PASS_STATE_FIELDS


def batch_workflow_locals(
    bindings: dict[str, dict],
    has_ecs_tasks: bool,
    has_lambda_tasks: bool,
    has_secret_tasks: bool,
) -> str:
    renderer = HCLRenderer()
    binding_expression = renderer.render_expression(bindings)
    fields = renderer.render_expression(sorted(PASS_STATE_FIELDS))
    if has_ecs_tasks:
        source = "local.ecs_workflow_definition"
    elif has_lambda_tasks:
        source = "local.lambda_workflow_definition"
    elif has_secret_tasks:
        source = "local.secret_workflow_definition"
    else:
        source = "var.definition"
    return (
        'data "aws_partition" "batch_tasks" {}\n'
        "locals {\n"
        f"  batch_bindings = {binding_expression}\n"
        f"  batch_source_workflow = jsondecode({source})\n"
        "  batch_task_states = { for name, parameters in local.batch_bindings : name => merge(\n"
        '    { for key, value in try(local.batch_source_workflow.States[name], {}) : key => value if !contains(["Type", "Result"], key) },\n'
        '    { Type = "Task", Resource = "arn:${data.aws_partition.batch_tasks.partition}:states:::batch:submitJob.sync", Parameters = parameters }\n'
        "  ) }\n"
        "  batch_workflow_definition = jsonencode(merge(local.batch_source_workflow, { States = merge(local.batch_source_workflow.States, local.batch_task_states) }))\n"
        "  batch_tasks_valid = try(\n"
        '    try(local.batch_source_workflow.QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        "    contains(keys(local.batch_source_workflow.States), local.batch_source_workflow.StartAt) &&\n"
        "    alltrue([for name, parameters in local.batch_bindings :\n"
        '      local.batch_source_workflow.States[name].Type == "Pass" &&\n'
        '      try(local.batch_source_workflow.States[name].QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        f"      length(setsubtract(toset(keys(local.batch_source_workflow.States[name])), toset({fields}))) == 0 &&\n"
        "      length(parameters.JobName) > 0 && length(parameters.JobQueue) > 0 && length(parameters.JobDefinition) > 0 &&\n"
        "      (\n"
        '        (try(local.batch_source_workflow.States[name].End, false) == true && !contains(keys(local.batch_source_workflow.States[name]), "Next")) ||\n'
        '        (!contains(keys(local.batch_source_workflow.States[name]), "End") && contains(keys(local.batch_source_workflow.States), try(local.batch_source_workflow.States[name].Next, "")))\n'
        "      )\n"
        "    ]), false\n"
        "  )\n"
        "}\n"
    )


def batch_workflow_attributes(
    has_ecs_tasks: bool, has_lambda_tasks: bool, has_secret_tasks: bool
) -> dict:
    dependencies = ["aws_iam_role_policy.batch_tasks"]
    preconditions = [
        {
            "condition": Expr("local.batch_tasks_valid"),
            "error_message": "Batch task bindings require top-level JSONPath Pass states, valid transitions, and job inputs.",
        }
    ]
    if has_ecs_tasks:
        dependencies.append("aws_iam_role_policy.ecs_tasks")
        preconditions.append(
            {
                "condition": Expr("local.ecs_tasks_valid"),
                "error_message": "ECS task bindings require top-level JSONPath Pass states, valid transitions, and task subnets.",
            }
        )
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
        "definition": Expr("local.batch_workflow_definition"),
        "depends_on": Expr(f"[{', '.join(dependencies)}]"),
        "lifecycle": {"precondition": preconditions},
    }
