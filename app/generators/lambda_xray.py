"""Lambda owns its regional X-Ray upload permissions."""

from app.generators.hcl_renderer import Expr, HCLRenderer


def render_lambda_xray_policy(name: str, renderer: HCLRenderer) -> str:
    return 'data "aws_region" "lambda_xray" {}\n\n' + renderer.render_resource(
        "aws_iam_role_policy",
        f"{name}_xray",
        {
            "name": f"{name}-xray",
            "role": Expr(f"aws_iam_role.{name}_role.id"),
            "policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords",
                            ],
                            "Resource": "*",
                            "Condition": {
                                "StringEquals": {
                                    "aws:RequestedRegion": Expr(
                                        "data.aws_region.lambda_xray.region"
                                    )
                                }
                            },
                        }
                    ],
                }
            ),
        },
    )


def lambda_tracing_precondition() -> dict:
    return {
        "condition": Expr('var.tracing_mode == "Active"'),
        "error_message": "Connected Lambda functions require Active X-Ray tracing.",
    }
