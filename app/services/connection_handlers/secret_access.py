"""Scoped runtime secret access policies owned by the consuming service."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


class SecretAccessHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        consumer = connection.source_name
        secret = connection.target_name
        peers = [
            item
            for item in project.connections
            if item.source_name == consumer
            and item.target_service == ServiceType.SECRETS_MANAGER
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        secrets = sorted({item.target_name for item in peers})
        result = ConnectionContribution()
        statements = []
        for index, name in enumerate(secrets):
            variable = f"runtime_secret_{index}_arn"
            result.inputs.append(
                self._input(
                    consumer,
                    "runtime",
                    f"secret_{index}_arn",
                    f"module.{name}.secret_arn",
                    "Secret available at runtime",
                )
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": Expr(f"var.{variable}"),
                }
            )
            keys = sorted(
                {
                    item.source_name
                    for item in project.connections
                    if item.source_service == ServiceType.KMS
                    and item.target_name == name
                    and item.connection_type == "encrypts"
                }
            )
            if len(keys) > 1:
                raise InvalidConnectionConfigError(
                    consumer,
                    secret,
                    connection.connection_type,
                    [
                        {
                            "loc": ("kms_key",),
                            "msg": "A secret can use only one managed KMS key",
                        },
                    ],
                )
            if keys:
                key_input = self._input(
                    consumer,
                    "runtime",
                    f"secret_{index}_key_arn",
                    f"module.{keys[0]}.key_arn",
                    "Key decrypting the runtime secret",
                )
                result.inputs.append(key_input)
                key_arn = Expr(f"var.{key_input.name}")
            else:
                instance = self._find_instance(name, project)
                if instance is None or not instance.config.kms_key_id:
                    continue
                result.outputs.append(
                    self._output(name, "configured_kms_key_id", "var.kms_key_id")
                )
                key_input = self._input(
                    consumer,
                    "runtime",
                    f"secret_{index}_key_id",
                    f"module.{name}.configured_kms_key_id",
                    "External secret encryption key",
                )
                result.inputs.append(key_input)
                result.resources.append(
                    self._resource(
                        consumer,
                        f"runtime_secret_{index}_key.tf",
                        f'data "aws_kms_key" "runtime_secret_{index}" {{\n  key_id = var.{key_input.name}\n}}\n',
                    )
                )
                key_arn = Expr(f"data.aws_kms_key.runtime_secret_{index}.arn")
            statements.append(
                {"Effect": "Allow", "Action": ["kms:Decrypt"], "Resource": key_arn}
            )
        result.resources.append(
            self._resource(
                consumer,
                "runtime_secrets_policy.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "runtime_secrets",
                    {
                        "name": f"{consumer}-runtime-secrets",
                        "role": Expr(f"aws_iam_role.{consumer}_role.id"),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
        return result
