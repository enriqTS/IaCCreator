"""Lambda Task states merged into a Step Functions workflow."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.workflow_states import PASS_STATE_FIELDS


def lambda_workflow_locals(bindings: dict[str, Expr], has_secret_tasks: bool) -> str:
    renderer = HCLRenderer()
    binding_expression = renderer.render_expression(bindings)
    fields = renderer.render_expression(list(PASS_STATE_FIELDS))
    source = (
        "local.secret_workflow_definition" if has_secret_tasks else "var.definition"
    )
    return (
        "locals {\n"
        f"  lambda_bindings = {binding_expression}\n"
        f"  lambda_source_workflow = jsondecode({source})\n"
        "  lambda_task_states = { for name, arn in local.lambda_bindings : name => merge(\n"
        '    { for key, value in try(local.lambda_source_workflow.States[name], {}) : key => value if !contains(["Type", "Result"], key) },\n'
        '    { Type = "Task", Resource = arn }\n'
        "  ) }\n"
        "  lambda_workflow_definition = jsonencode(merge(local.lambda_source_workflow, { States = merge(local.lambda_source_workflow.States, local.lambda_task_states) }))\n"
        "  lambda_tasks_valid = try(\n"
        '    try(local.lambda_source_workflow.QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        "    contains(keys(local.lambda_source_workflow.States), local.lambda_source_workflow.StartAt) &&\n"
        "    alltrue([for name in keys(local.lambda_bindings) :\n"
        '      local.lambda_source_workflow.States[name].Type == "Pass" &&\n'
        '      try(local.lambda_source_workflow.States[name].QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        f"      length(setsubtract(toset(keys(local.lambda_source_workflow.States[name])), toset({fields}))) == 0 &&\n"
        "      (\n"
        '        (try(local.lambda_source_workflow.States[name].End, false) == true && !contains(keys(local.lambda_source_workflow.States[name]), "Next")) ||\n'
        '        (!contains(keys(local.lambda_source_workflow.States[name]), "End") && contains(keys(local.lambda_source_workflow.States), try(local.lambda_source_workflow.States[name].Next, "")))\n'
        "      )\n"
        "    ]), false\n"
        "  )\n"
        "}\n"
    )


def lambda_workflow_attributes(has_secret_tasks: bool) -> dict:
    dependencies = ["aws_iam_role_policy.lambda_tasks"]
    preconditions = [
        {
            "condition": Expr("local.lambda_tasks_valid"),
            "error_message": "Lambda task bindings require top-level JSONPath Pass states with valid transitions and supported fields.",
        }
    ]
    if has_secret_tasks:
        dependencies.append("aws_iam_role_policy.runtime_secrets")
        preconditions.append(
            {
                "condition": Expr("local.secret_tasks_valid"),
                "error_message": "Secret task bindings require top-level JSONPath Pass states with valid transitions and supported fields.",
            }
        )
    return {
        "definition": Expr("local.lambda_workflow_definition"),
        "depends_on": Expr(f"[{', '.join(dependencies)}]"),
        "lifecycle": {"precondition": preconditions},
    }
