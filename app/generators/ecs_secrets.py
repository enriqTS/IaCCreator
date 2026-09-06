"""Merge native secret references into caller-supplied container definitions."""

from app.generators.hcl_renderer import Expr


def secret_task_attributes(instance_name: str) -> dict:
    managed = "[for secret in local.runtime_secrets : secret.name if secret.container == container.name]"
    return {
        "execution_role_arn": Expr(f"aws_iam_role.{instance_name}_role.arn"),
        "depends_on": Expr(
            f"[aws_iam_role_policy.runtime_secrets, aws_iam_role_policy.{instance_name}_policy]"
        ),
        "container_definitions": Expr(
            "jsonencode([for container in jsondecode(var.container_definitions) : merge(container, {"
            "secrets = concat("
            f"[for secret in try(container.secrets, []) : secret if !contains({managed}, secret.name)], "
            "[for secret in local.runtime_secrets : {name = secret.name, valueFrom = secret.valueFrom} "
            "if secret.container == container.name]), "
            f"environment = [for item in try(container.environment, []) : item if !contains({managed}, item.name)]"
            "})])"
        ),
        "lifecycle": {
            "precondition": {
                "condition": Expr(
                    "alltrue([for secret in local.runtime_secrets : "
                    "contains([for container in jsondecode(var.container_definitions) : container.name], secret.container)])"
                ),
                "error_message": "Every secret connection must name a container in container_definitions.",
            },
        },
    }
