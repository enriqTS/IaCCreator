"""Native MemoryDB lifecycle checks for IAM clients and existing users."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.memorydb_config import MEMORYDB_IAM_VERSION_PATTERN


def client_lifecycle(explicit_version: bool) -> dict:
    pattern = HCLRenderer().render_expression(MEMORYDB_IAM_VERSION_PATTERN)
    preconditions = [
        {
            "condition": Expr(
                'var.tls_enabled && lower(trimspace(var.acl_name)) != "open-access" && trimspace(var.acl_name) != ""'
            ),
            "error_message": "MemoryDB IAM login requires TLS and an explicit ACL containing the IAM user.",
        }
    ]
    if explicit_version:
        preconditions.append(
            {
                "condition": Expr(f"can(regex({pattern}, var.engine_version))"),
                "error_message": "MemoryDB IAM login requires engine 7.0 or newer.",
            }
        )
    return {
        "precondition": preconditions,
        "postcondition": {
            "condition": Expr(f"can(regex({pattern}, self.engine_version))"),
            "error_message": "MemoryDB IAM login requires engine 7.0 or newer.",
        },
    }


def existing_user(identifier: str, username: str) -> str:
    renderer = HCLRenderer()
    attrs = {
        "user_name": username,
        "lifecycle": {
            "postcondition": [
                {
                    "condition": Expr('one(self.authentication_mode).type == "iam"'),
                    "error_message": "Selected MemoryDB user must use IAM authentication.",
                },
                {
                    "condition": Expr(
                        "contains(data.aws_memorydb_acl.iam_client.user_names, self.user_name)"
                    ),
                    "error_message": "Selected MemoryDB user must belong to the cluster ACL.",
                },
            ]
        },
    }
    return renderer.render_resource("aws_memorydb_user", identifier, attrs).replace(
        "resource ", "data ", 1
    )


def existing_acl() -> str:
    return (
        HCLRenderer()
        .render_resource(
            "aws_memorydb_acl", "iam_client", {"name": Expr("var.acl_name")}
        )
        .replace("resource ", "data ", 1)
    )
