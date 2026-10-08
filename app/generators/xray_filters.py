"""Native producer identities constrain X-Ray group membership."""

from app.generators.hcl_renderer import Expr

XRAY_GROUP_NAME_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"


def lambda_group_selectors() -> Expr:
    return Expr(
        '[for function in values(var.xray_lambda_functions) : format("(service(id(name: %s, type: %s, account.id: %s)) OR service(id(name: %s, type: %s, account.id: %s)))", jsonencode(function.name), jsonencode("AWS::Lambda"), jsonencode(try(split(":", function.arn)[4], "")), jsonencode(function.name), jsonencode("AWS::Lambda::Function"), jsonencode(try(split(":", function.arn)[4], "")))]'
    )


def group_filter_expression(selectors: list[Expr]) -> Expr:
    members = (
        selectors[0] if len(selectors) == 1 else "concat(" + ", ".join(selectors) + ")"
    )
    return Expr(
        f'format("(%s) AND (%s)", join(" OR ", {members}), var.filter_expression)'
    )


def lambda_group_filter_expression() -> Expr:
    return group_filter_expression([lambda_group_selectors()])


def lambda_group_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.xray_lambda_functions) > 0 && alltrue([for function in values(var.xray_lambda_functions) : can(regex("^arn:[^:]+:lambda:[^:]+:[0-9]{12}:function:[A-Za-z0-9_-]{1,64}$", function.arn)) && function.name == try(split(":", function.arn)[6], "")])'
            ),
            "error_message": "X-Ray group members require native unqualified Lambda function identities.",
        },
        {
            "condition": Expr(
                'alltrue([for function in values(var.xray_lambda_functions) : try(split(":", function.arn)[1], "") == data.aws_partition.xray_tracing.partition && try(split(":", function.arn)[3], "") == data.aws_region.xray_tracing.region && try(split(":", function.arn)[4], "") == data.aws_caller_identity.xray_tracing.account_id])'
            ),
            "error_message": "Lambda functions and their X-Ray group must share a partition, Region, and account.",
        },
        *group_configuration_preconditions(),
    ]


def group_configuration_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                f'can(regex("{XRAY_GROUP_NAME_PATTERN}", var.group_name)) && var.group_name != "Default" && length(trimspace(var.filter_expression)) > 0'
            ),
            "error_message": "Managed X-Ray groups require a concrete non-reserved name and a nonempty additional trace filter.",
        },
        {
            "condition": Expr("!var.notifications_enabled || var.insights_enabled"),
            "error_message": "X-Ray Insights notifications require Insights to be enabled.",
        },
    ]


def render_xray_scope_data() -> str:
    return "\n".join(
        f'data "{kind}" "xray_tracing" {{}}\n'
        for kind in ["aws_partition", "aws_region", "aws_caller_identity"]
    )
