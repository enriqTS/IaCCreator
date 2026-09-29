"""Shared naming and service-role trust for AppSync data sources."""

from hashlib import sha256

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.services.connection_handlers.base import safe_identifier


def data_source_name(kind: str, target: str) -> str:
    suffix = sha256(f"{kind}.{target}".encode()).hexdigest()[:8]
    return f"{kind}_{safe_identifier(target)[:40]}_{suffix}"


def resolver_name(type_name: str, field_name: str) -> str:
    suffix = sha256(f"{type_name}.{field_name}".encode()).hexdigest()[:8]
    return f"resolver_{type_name[:24]}_{field_name[:24]}_{suffix}"


def assume_role_policy(renderer: HCLRenderer, api: str) -> Expr:
    return renderer.render_json_policy(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "appsync.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "ArnEquals": {
                            "aws:SourceArn": Expr(f"aws_appsync_graphql_api.{api}.arn")
                        }
                    },
                }
            ],
        }
    )
