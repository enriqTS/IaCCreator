"""Workspace roles share native permission guards and pre-creation trust scopes."""

from app.generators.hcl_renderer import Expr, HCLRenderer


def grafana_workspace_attributes(name: str) -> dict:
    return {
        "role_arn": Expr(f"aws_iam_role.{name}_data_sources.arn"),
        "depends_on": [Expr(f"aws_iam_role_policy.{name}_data_sources")],
        "lifecycle": {
            "precondition": [
                {
                    "condition": Expr('var.permission_type == "CUSTOMER_MANAGED"'),
                    "error_message": "Managed data-source connections require customer-managed Grafana permissions.",
                },
                {
                    "condition": Expr('var.account_access_type == "CURRENT_ACCOUNT"'),
                    "error_message": "Managed data-source connections support current-account Grafana workspaces only.",
                },
            ]
        },
    }


def render_grafana_role(
    name: str,
    statements: list[dict | Expr],
    preconditions: list[dict],
    renderer: HCLRenderer,
) -> str:
    resource = f"{name}_data_sources"
    content = 'data "aws_partition" "grafana_sources" {}\ndata "aws_region" "grafana_sources" {}\ndata "aws_caller_identity" "grafana_sources" {}\n\n'
    content += renderer.render_resource(
        "aws_iam_role",
        resource,
        {
            "name_prefix": "grafana-data-sources-",
            "assume_role_policy": renderer.render_json_policy(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Principal": {
                                "Service": Expr(
                                    '"grafana.${data.aws_partition.grafana_sources.dns_suffix}"'
                                )
                            },
                            "Condition": {
                                "StringEquals": {
                                    "aws:SourceAccount": Expr(
                                        "data.aws_caller_identity.grafana_sources.account_id"
                                    )
                                },
                                "ArnLike": {
                                    "aws:SourceArn": Expr(
                                        '"arn:${data.aws_partition.grafana_sources.partition}:grafana:${data.aws_region.grafana_sources.region}:${data.aws_caller_identity.grafana_sources.account_id}:/workspaces/*"'
                                    )
                                },
                            },
                        }
                    ],
                }
            ),
        },
    )
    attrs = {
        "name_prefix": "grafana-data-sources-",
        "role": Expr(f"aws_iam_role.{resource}.id"),
        "policy": renderer.render_json_policy(
            {
                "Version": "2012-10-17",
                "Statement": Expr(f"flatten({renderer.render_expression(statements)})"),
            }
        ),
    }
    if preconditions:
        attrs["lifecycle"] = {"precondition": preconditions}
    return (
        content
        + "\n"
        + renderer.render_resource("aws_iam_role_policy", resource, attrs)
    )
