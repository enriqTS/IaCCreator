"""Relational IAM login grants and connection metadata without database credentials."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.database_auth import IAM_DATABASE_ENGINES, iam_database_expressions
from app.models.connection_configs.database import DatabaseIamAuthConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class DatabaseAccessHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Create the selected database user and enable its engine-specific IAM authentication separately; SQL grants determine read/write access. Application code must generate IAM tokens using the exported host, port, and Region and connect over TLS. VPC routing and security groups remain separate. New databases require explicit master-password management; Aurora also requires provisioned cluster instances. Verify engine-version and Region support. No passwords or tokens are retrieved or exposed by this connection.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = DatabaseIamAuthConfig.model_validate(connection.connection_config)
        database = self._find_instance(connection.target_name, project)
        if database.config.engine not in IAM_DATABASE_ENGINES[database.service_type]:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("engine",),
                        "msg": "IAM authentication requires a supported database engine",
                    }
                ],
            )
        database.config._iam_database_access = True
        source, target = connection.source_name, connection.target_name
        expressions = iam_database_expressions(database.service_type, target)
        result = ConnectionContribution()
        for field, expression in expressions.items():
            output = f"iam_database_{field}"
            variable = f"database_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            )
            if field != "iam_resource_arn":
                result.outputs.append(
                    self._output(
                        source,
                        variable,
                        f"var.{variable}",
                        "IAM database client connection metadata",
                    )
                )
        result.iam.append(
            self._grant(
                source,
                IAMStatement(
                    actions=["rds-db:connect"],
                    resources=[
                        "${var.database_"
                        + target
                        + "_iam_resource_arn}/"
                        + config.database_user
                    ],
                ),
            )
        )
        return result
