"""Native regional upload policies stay independent of query groups."""

from app.generators.hcl_renderer import Expr, HCLRenderer


def render_xray_upload_policy(
    name: str, renderer: HCLRenderer, region: str, *, telemetry: bool
) -> str:
    actions = ["xray:PutTraceSegments"]
    if telemetry:
        actions.append("xray:PutTelemetryRecords")
    return renderer.render_resource(
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
                            "Action": actions,
                            "Resource": "*",
                            "Condition": {
                                "StringEquals": {"aws:RequestedRegion": Expr(region)}
                            },
                        }
                    ],
                }
            ),
        },
    )
