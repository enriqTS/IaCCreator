"""Emits the IAM role and inline policy for any service that assumes one."""

from __future__ import annotations

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class ExecutionRoleGenerator:
    """Generates iam.tf for a resource whose config declares an execution role."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_iam_tf(self, instance: ResourceInstanceIR) -> str:
        """Render the role and the policy that loads its JSON document."""
        principal = type(instance.config).execution_role_principal
        if principal is None:
            return ""

        name = instance.name
        role_block = self._r.render_resource(
            "aws_iam_role",
            f"{name}_role",
            {
                "name": f"{name}-role",
                "assume_role_policy": self._r.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": "sts:AssumeRole",
                                "Effect": "Allow",
                                "Principal": {"Service": principal},
                            }
                        ],
                    },
                    depth=2,
                ),
            },
        )

        policy_path = f"${{path.root}}/../../iam-policies/{name}-policy.json"
        policy_block = self._r.render_resource(
            "aws_iam_role_policy",
            f"{name}_policy",
            {
                "name": f"{name}-policy",
                "role": Expr(f"aws_iam_role.{name}_role.id"),
                "policy": Expr(f'file("{policy_path}")'),
            },
        )

        return role_block + "\n" + policy_block
