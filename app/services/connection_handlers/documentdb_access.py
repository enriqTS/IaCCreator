"""DocumentDB clients authenticate with runtime roles mapped in the external database."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models.ecs_config import EcsConfig
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class DocumentDbAccessHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Exports MONGODB-AWS client configuration for an instance-based DocumentDB 5.0 cluster. Before connecting, a database administrator must create a $external user matching the exported runtime role ARN and assign database roles. No IAM data-access policy grants database permissions. Requires separately provisioned cluster instances, administrator credentials, network reachability, and a compatible driver with the AWS CA bundle. Application code uses TLS and runtime role credentials. No database users, passwords, or tokens are created.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        cluster = self._find_instance(connection.target_name, project)
        if cluster.config.engine_version != "5.0":
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("engine_version",),
                        "msg": "Select DocumentDB engine version 5.0 for IAM client connections",
                    }
                ],
            )
        cluster.config._iam_client_access = True
        consumer = self._find_instance(connection.source_name, project)
        if isinstance(consumer.config, EcsConfig):
            consumer.config._requires_task_role = True
        source, target = connection.source_name, connection.target_name
        resource = f"aws_docdb_cluster.{target}"
        result = ConnectionContribution()
        metadata = {}
        for field, expression in {
            "host": f"{resource}.endpoint",
            "reader_host": f"{resource}.reader_endpoint",
            "port": f"tostring({resource}.port)",
        }.items():
            output, variable = f"iam_client_{field}", f"documentdb_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            )
            metadata[field] = Expr(f"var.{variable}")
        metadata.update(
            {
                "role_arn": Expr(f"aws_iam_role.{source}_role.arn"),
                "auth_mechanism": "MONGODB-AWS",
                "auth_source": "$external",
                "tls": True,
                "replica_set": "rs0",
                "retry_writes": False,
            }
        )
        result.outputs.append(
            self._output(
                source,
                f"documentdb_{target}_iam_client",
                self._renderer.render_expression(metadata),
                "DocumentDB IAM client settings; database role mapping must be provisioned separately",
            )
        )
        return result
