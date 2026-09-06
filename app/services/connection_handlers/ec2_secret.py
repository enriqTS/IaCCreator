"""Connection-owned EC2 credentials for runtime secret retrieval."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.secret_access import SecretAccessHandler


class Ec2SecretHandler(SecretAccessHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        result = super().handle(connection, project)
        if not result.resources:
            return result
        instance = self._find_instance(connection.source_name, project)
        if instance is not None:
            instance.config._reads_runtime_secrets = True
        name = connection.source_name
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
        result.resources.append(
            self._resource(name, "runtime_secrets_role.tf", role + "\n" + profile)
        )
        return result
