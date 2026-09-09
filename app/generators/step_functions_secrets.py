"""Executable secret tasks merged into the caller's workflow definition."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.workflow_states import PASS_STATE_FIELDS


def secret_workflow_locals(bindings: dict[str, Expr]) -> str:
    renderer = HCLRenderer()
    binding_expression = renderer.render_expression(bindings)
    fields = renderer.render_expression(list(PASS_STATE_FIELDS))
    return (
        'data "aws_partition" "secret_tasks" {}\n'
        "locals {\n"
        f"  secret_bindings = {binding_expression}\n"
        "  secret_source_workflow = jsondecode(var.definition)\n"
        "  secret_task_states = { for name, arn in local.secret_bindings : name => merge(\n"
        '    { for key, value in try(local.secret_source_workflow.States[name], {}) : key => value if !contains(["Type", "Result"], key) },\n'
        '    { Type = "Task", Resource = "arn:${data.aws_partition.secret_tasks.partition}:states:::aws-sdk:secretsmanager:getSecretValue", Parameters = { SecretId = arn } }\n'
        "  ) }\n"
        "  secret_workflow_definition = jsonencode(merge(local.secret_source_workflow, { States = merge(local.secret_source_workflow.States, local.secret_task_states) }))\n"
        "  secret_tasks_valid = try(\n"
        '    try(local.secret_source_workflow.QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        "    contains(keys(local.secret_source_workflow.States), local.secret_source_workflow.StartAt) &&\n"
        "    alltrue([for name in keys(local.secret_bindings) :\n"
        '      local.secret_source_workflow.States[name].Type == "Pass" &&\n'
        '      try(local.secret_source_workflow.States[name].QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        f"      length(setsubtract(toset(keys(local.secret_source_workflow.States[name])), toset({fields}))) == 0 &&\n"
        "      (\n"
        '        (try(local.secret_source_workflow.States[name].End, false) == true && !contains(keys(local.secret_source_workflow.States[name]), "Next")) ||\n'
        '        (!contains(keys(local.secret_source_workflow.States[name]), "End") && contains(keys(local.secret_source_workflow.States), try(local.secret_source_workflow.States[name].Next, "")))\n'
        "      )\n"
        "    ]), false\n"
        "  )\n"
        "}\n"
    )


def secret_workflow_attributes() -> dict:
    return {
        "definition": Expr("local.secret_workflow_definition"),
        "depends_on": Expr("[aws_iam_role_policy.runtime_secrets]"),
        "lifecycle": {
            "precondition": {
                "condition": Expr("local.secret_tasks_valid"),
                "error_message": "Secret task bindings require top-level JSONPath Pass states with valid transitions and supported fields.",
            }
        },
    }
