"""SNS Publish states merged into workflow definitions."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.workflow_states import PASS_STATE_FIELDS


def sns_workflow_locals(
    bindings: dict[str, dict],
    has_batch_tasks: bool,
    has_ecs_tasks: bool,
    has_lambda_tasks: bool,
    has_secret_tasks: bool,
) -> str:
    renderer = HCLRenderer()
    binding_expression = renderer.render_expression(bindings)
    fields = renderer.render_expression(sorted(PASS_STATE_FIELDS))
    if has_batch_tasks:
        source = "local.batch_workflow_definition"
    elif has_ecs_tasks:
        source = "local.ecs_workflow_definition"
    elif has_lambda_tasks:
        source = "local.lambda_workflow_definition"
    elif has_secret_tasks:
        source = "local.secret_workflow_definition"
    else:
        source = "var.definition"
    return (
        'data "aws_partition" "sns_tasks" {}\n'
        "locals {\n"
        f"  sns_bindings = {binding_expression}\n"
        f"  sns_source_workflow = jsondecode({source})\n"
        "  sns_task_states = { for name, parameters in local.sns_bindings : name => merge(\n"
        '    { for key, value in try(local.sns_source_workflow.States[name], {}) : key => value if !contains(["Type", "Result"], key) },\n'
        '    { Type = "Task", Resource = "arn:${data.aws_partition.sns_tasks.partition}:states:::sns:publish", Parameters = parameters }\n'
        "  ) }\n"
        "  sns_workflow_definition = jsonencode(merge(local.sns_source_workflow, { States = merge(local.sns_source_workflow.States, local.sns_task_states) }))\n"
        "  sns_tasks_valid = try(\n"
        '    try(local.sns_source_workflow.QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        "    contains(keys(local.sns_source_workflow.States), local.sns_source_workflow.StartAt) &&\n"
        "    alltrue([for name, parameters in local.sns_bindings :\n"
        '      local.sns_source_workflow.States[name].Type == "Pass" &&\n'
        '      try(local.sns_source_workflow.States[name].QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        f"      length(setsubtract(toset(keys(local.sns_source_workflow.States[name])), toset({fields}))) == 0 &&\n"
        "      length(parameters.TopicArn) > 0 &&\n"
        "      (\n"
        '        (try(local.sns_source_workflow.States[name].End, false) == true && !contains(keys(local.sns_source_workflow.States[name]), "Next")) ||\n'
        '        (!contains(keys(local.sns_source_workflow.States[name]), "End") && contains(keys(local.sns_source_workflow.States), try(local.sns_source_workflow.States[name].Next, "")))\n'
        "      )\n"
        "    ]), false\n"
        "  )\n"
        "}\n"
    )


def sns_workflow_attributes(
    has_batch_tasks: bool,
    has_ecs_tasks: bool,
    has_lambda_tasks: bool,
    has_secret_tasks: bool,
) -> dict:
    dependencies = ["aws_iam_role_policy.sns_tasks"]
    preconditions = [
        {
            "condition": Expr("local.sns_tasks_valid"),
            "error_message": "SNS task bindings require top-level JSONPath Pass states, valid transitions, and topic ARNs.",
        }
    ]
    prior = (
        (has_batch_tasks, "batch_tasks", "Batch"),
        (has_ecs_tasks, "ecs_tasks", "ECS"),
        (has_lambda_tasks, "lambda_tasks", "Lambda"),
        (has_secret_tasks, "runtime_secrets", "Secret"),
    )
    for enabled, policy, label in prior:
        if not enabled:
            continue
        dependencies.append(f"aws_iam_role_policy.{policy}")
        name = "secret_tasks" if policy == "runtime_secrets" else policy
        preconditions.append(
            {
                "condition": Expr(f"local.{name}_valid"),
                "error_message": f"{label} task bindings require valid JSONPath Pass states and transitions.",
            }
        )
    return {
        "definition": Expr("local.sns_workflow_definition"),
        "depends_on": Expr(f"[{', '.join(dependencies)}]"),
        "lifecycle": {"precondition": preconditions},
    }
