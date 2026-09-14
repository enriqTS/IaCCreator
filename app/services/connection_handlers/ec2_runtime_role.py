"""Shared EC2 runtime identity preserves existing secret-access resource addresses."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution
from app.services.connection_handlers.base import BaseConnectionHandler


class Ec2RuntimeRole(BaseConnectionHandler):
    def build(self, name: str) -> ConnectionContribution:
        role = self._renderer.render_resource(
            "aws_iam_role",
            f"{name}_role",
            {
                "name_prefix": "runtime-secrets-",
                "assume_role_policy": self._renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": "sts:AssumeRole",
                                "Principal": {"Service": "ec2.amazonaws.com"},
                            }
                        ],
                    }
                ),
            },
        )
        profile = self._renderer.render_resource(
            "aws_iam_instance_profile",
            "runtime_secrets",
            {
                "name_prefix": "runtime-secrets-",
                "role": Expr(f"aws_iam_role.{name}_role.name"),
            },
        )
        result = ConnectionContribution()
        result.resources.append(
            self._resource(name, "runtime_secrets_role.tf", role + "\n" + profile)
        )
        return result
