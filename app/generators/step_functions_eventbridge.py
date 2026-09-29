"""EventBridge PutEvents tasks merged into workflow definitions."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.workflow_states import PASS_STATE_FIELDS


def eventbridge_workflow_locals(
    bindings: dict[str, dict],
    has_dynamodb_tasks: bool,
    has_sqs_tasks: bool,
    has_sns_tasks: bool,
    has_batch_tasks: bool,
    has_ecs_tasks: bool,
    has_lambda_tasks: bool,
    has_secret_tasks: bool,
) -> str:
    renderer = HCLRenderer()
    binding_expression = renderer.render_expression(bindings)
    fields = renderer.render_expression(sorted(PASS_STATE_FIELDS))
    prior = (
        (has_dynamodb_tasks, "local.dynamodb_workflow_definition"),
        (has_sqs_tasks, "local.sqs_workflow_definition"),
        (has_sns_tasks, "local.sns_workflow_definition"),
        (has_batch_tasks, "local.batch_workflow_definition"),
        (has_ecs_tasks, "local.ecs_workflow_definition"),
        (has_lambda_tasks, "local.lambda_workflow_definition"),
        (has_secret_tasks, "local.secret_workflow_definition"),
    )
    source = next((name for present, name in prior if present), "var.definition")
    return (
        'data "aws_partition" "eventbridge_tasks" {}\n'
        "locals {\n"
        f"  eventbridge_bindings = {binding_expression}\n"
        f"  eventbridge_source_workflow = jsondecode({source})\n"
        "  eventbridge_task_states = { for name, parameters in local.eventbridge_bindings : name => merge(\n"
        '    { for key, value in try(local.eventbridge_source_workflow.States[name], {}) : key => value if !contains(["Type", "Result"], key) },\n'
        '    { Type = "Task", Resource = "arn:${data.aws_partition.eventbridge_tasks.partition}:states:::events:putEvents", Parameters = parameters }\n'
        "  ) }\n"
        "  eventbridge_workflow_definition = jsonencode(merge(local.eventbridge_source_workflow, { States = merge(local.eventbridge_source_workflow.States, local.eventbridge_task_states) }))\n"
        "  eventbridge_tasks_valid = try(\n"
        '    try(local.eventbridge_source_workflow.QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        "    contains(keys(local.eventbridge_source_workflow.States), local.eventbridge_source_workflow.StartAt) &&\n"
        "    alltrue([for name, parameters in local.eventbridge_bindings :\n"
        '      local.eventbridge_source_workflow.States[name].Type == "Pass" &&\n'
        '      try(local.eventbridge_source_workflow.States[name].QueryLanguage, "JSONPath") == "JSONPath" &&\n'
        f"      length(setsubtract(toset(keys(local.eventbridge_source_workflow.States[name])), toset({fields}))) == 0 &&\n"
        "      length(parameters.Entries[0].EventBusName) > 0 &&\n"
        "      (\n"
        '        (try(local.eventbridge_source_workflow.States[name].End, false) == true && !contains(keys(local.eventbridge_source_workflow.States[name]), "Next")) ||\n'
        '        (!contains(keys(local.eventbridge_source_workflow.States[name]), "End") && contains(keys(local.eventbridge_source_workflow.States), try(local.eventbridge_source_workflow.States[name].Next, "")))\n'
        "      )\n"
        "    ]), false\n"
        "  )\n"
        "}\n"
    )


def eventbridge_workflow_attributes(
    has_dynamodb_tasks: bool,
    has_sqs_tasks: bool,
    has_sns_tasks: bool,
    has_batch_tasks: bool,
    has_ecs_tasks: bool,
    has_lambda_tasks: bool,
    has_secret_tasks: bool,
) -> dict:
    dependencies = ["aws_iam_role_policy.eventbridge_tasks"]
    preconditions = [
        {
            "condition": Expr("local.eventbridge_tasks_valid"),
            "error_message": "EventBridge task bindings require top-level JSONPath Pass states, valid transitions, and event bus ARNs.",
        }
    ]
    prior = (
        (has_dynamodb_tasks, "dynamodb_tasks", "DynamoDB"),
        (has_sqs_tasks, "sqs_tasks", "SQS"),
        (has_sns_tasks, "sns_tasks", "SNS"),
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
        "definition": Expr("local.eventbridge_workflow_definition"),
        "depends_on": Expr(f"[{', '.join(dependencies)}]"),
        "lifecycle": {"precondition": preconditions},
    }
