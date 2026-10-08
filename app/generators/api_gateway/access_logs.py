"""Native access-log destinations stay in the existing stage resource."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.api_gateway_logs import REQUEST_ID_PATTERN


def access_log_preconditions(stage_name: str, renderer: HCLRenderer) -> list[dict]:
    key = renderer.render_expression(stage_name)
    arn = f"var.api_access_logs[{key}].arn"
    log_format = f"var.api_access_logs[{key}].format"
    request_id = renderer.render_expression(REQUEST_ID_PATTERN)
    return [
        {
            "condition": Expr(
                f'can(regex("^arn:[^:]+:logs:[^:]+:[0-9]{{12}}:log-group:[A-Za-z0-9_./#-]+$", trimsuffix({arn}, ":*")))'
            ),
            "error_message": "HTTP access logging requires a native CloudWatch log-group ARN.",
        },
        {
            "condition": Expr(
                f'try(split(":", {arn})[1], "") == data.aws_partition.api_access_logs.partition && try(split(":", {arn})[3], "") == data.aws_region.api_access_logs.region && try(split(":", {arn})[4], "") == data.aws_caller_identity.api_access_logs.account_id'
            ),
            "error_message": "The API stage and log group must share a partition, Region, and account.",
        },
        {
            "condition": Expr(
                f'var.protocol_type == "HTTP" && can(regex({request_id}, {log_format})) && length(regexall("[\\n\\r]", {log_format})) == 0'
            ),
            "error_message": "Managed HTTP access logs require a single-line format containing $context.requestId.",
        },
    ]


def access_log_attributes(stage_name: str, renderer: HCLRenderer) -> dict:
    key = renderer.render_expression(stage_name)
    return {
        "access_log_settings": {
            "destination_arn": Expr(
                f'trimsuffix(var.api_access_logs[{key}].arn, ":*")'
            ),
            "format": Expr(f"var.api_access_logs[{key}].format"),
        },
        "lifecycle": {"precondition": access_log_preconditions(stage_name, renderer)},
    }
