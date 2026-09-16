"""DMS owns relational IAM endpoint resources while databases export native identities."""

import re
from typing import Literal

from app.exceptions import InvalidConnectionConfigError
from app.generators.database_auth import IAM_DATABASE_ENGINES, iam_database_expressions
from app.generators.dms_iam_endpoint import render_iam_endpoint
from app.generators.dms_identifiers import dms_identifier
from app.models.connection_configs.dms import DmsIamEndpointConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.input_models.dms_config import DMS_IAM_VERSION_PATTERN
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class DmsDatabaseEndpointHandler(BaseConnectionHandler):
    def __init__(self, endpoint_type: Literal["source", "target"]):
        super().__init__()
        self._endpoint_type = endpoint_type

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Creates an IAM-authenticated DMS endpoint and a dedicated database-login role. Requires DMS 3.6.1 or newer, an existing IAM-enabled database user with migration-specific SQL grants, and a CA certificate imported into DMS in the replication instance's account and Region. Enables native IAM authentication on the database and uses verify-ca TLS. Database provisioning, network access, DMS account roles, test-connection, and CDC prerequisites remain separate. Full-load tasks and table mappings can be added through a replication_task connection. Treat this endpoint as full-load configuration until CDC support is verified for the selected engines. No passwords or secret values are created or read; the deployment identity needs iam:PassRole for the endpoint role.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = DmsIamEndpointConfig.model_validate(connection.connection_config)
        database = self._find_instance(connection.target_name, project)
        instance = self._find_instance(connection.source_name, project)
        if database.config.engine not in IAM_DATABASE_ENGINES[database.service_type]:
            self._reject(
                connection,
                "DMS IAM endpoints require supported RDS/Aurora MySQL, MariaDB, or PostgreSQL engines",
            )
        if instance.config.engine_version is None or not re.match(
            DMS_IAM_VERSION_PATTERN, instance.config.engine_version
        ):
            self._reject(
                connection,
                "Select DMS replication engine 3.6.1 or newer for IAM endpoints",
            )
        for other in project.connections:
            if (
                other.source_service == ServiceType.DATABASE_MIGRATION_SERVICE
                and other.connection_type in {"source_endpoint", "target_endpoint"}
                and other.connection_config.get("endpoint_id") == config.endpoint_id
                and (
                    other.source_name,
                    other.target_name,
                    other.connection_type,
                    other.connection_config,
                )
                != (
                    connection.source_name,
                    connection.target_name,
                    connection.connection_type,
                    connection.connection_config,
                )
            ):
                self._reject(
                    connection,
                    "DMS endpoint identifiers must be unique across this project",
                )
        database.config._iam_database_access = True
        instance.config._iam_endpoints = True
        source, target = connection.source_name, connection.target_name
        identifier = dms_identifier("endpoint", config.endpoint_id)
        resource = f"{'aws_rds_cluster' if database.service_type == ServiceType.AURORA else 'aws_db_instance'}.{target}"
        expressions = iam_database_expressions(database.service_type, target)
        expressions["engine"] = f"{resource}.engine"
        result = ConnectionContribution()
        for field in ("host", "port", "iam_resource_arn", "engine"):
            output = f"iam_database_{field}"
            result.outputs.append(self._output(target, output, expressions[field]))
            result.inputs.append(
                ModuleInput(
                    module=source,
                    name=f"dms_database_{target}_{field}",
                    value=f"module.{target}.{output}",
                )
            )
        result.resources.extend(
            [
                self._resource(
                    source,
                    "dms_endpoint_partition.tf",
                    'data "aws_partition" "dms_endpoints" {}\n',
                ),
                self._resource(
                    source,
                    f"{identifier}.tf",
                    render_iam_endpoint(
                        config,
                        self._endpoint_type,
                        database.config.engine,
                        identifier,
                        source,
                        target,
                    ),
                ),
            ]
        )
        result.outputs.append(
            self._output(
                source,
                f"{identifier}_arn",
                f"aws_dms_endpoint.{identifier}.endpoint_arn",
                f"DMS {self._endpoint_type} endpoint {config.endpoint_id}",
            )
        )
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("dms",), "msg": message}],
        )
