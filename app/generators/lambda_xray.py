"""Lambda owns its regional X-Ray upload permissions."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.xray_upload import render_xray_upload_policy


def render_lambda_xray_policy(name: str, renderer: HCLRenderer) -> str:
    return 'data "aws_region" "lambda_xray" {}\n\n' + render_xray_upload_policy(
        name, renderer, "data.aws_region.lambda_xray.region", telemetry=True
    )


def lambda_tracing_precondition() -> dict:
    return {
        "condition": Expr('var.tracing_mode == "Active"'),
        "error_message": "Connected Lambda functions require Active X-Ray tracing.",
    }
