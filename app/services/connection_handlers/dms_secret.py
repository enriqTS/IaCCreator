"""Connect relational DMS endpoints through externally prepared secrets."""

from typing import Literal

from app.exceptions import InvalidConnectionConfigError
from app.generators.dms_identifiers import dms_identifier
from app.generators.dms_secret_endpoint import render_secret_endpoint
from app.generators.dms_secret_engines import DMS_SECRET_ENGINES
from app.models.connection_configs.dms import DmsSecretEndpointConfig
from app.models.connection_configs.dms_source import DmsSecretSourceEndpointConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.dms_endpoints import validate_endpoint_identity


class DmsSecretEndpointHandler(BaseConnectionHandler):
    def __init__(self, endpoint_type: Literal["source", "target"]):
        super().__init__()
        self._endpoint_type = endpoint_type

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="References an existing database secret and DMS-trusted access role. The secret must contain host, port, username and password for the selected database; secret contents and role permissions are not verified. Prepare GetSecretValue and any customer-key decryption permissions, SQL migration grants, network access, and an imported DMS CA certificate. Uses verify-full TLS for SQL Server and verify-ca for other supported engines, without reading credentials into Terraform. SQL Server requires SQL authentication and a secret hostname matching the certificate; Windows authentication is unsupported. SQL Server CDC requires DMS 3.5.3 or newer, externally enabled MS-CDC for the database and selected tables, and transaction-log backup access. Oracle requires an auto-login wallet imported into DMS, a secret using the TLS listener port, and database_name selecting the Oracle service or PDB. Non-CDB Oracle CDC defaults to LogMiner and requires supplemental logging, retained archive logs, and SQL grants; CDB/PDB CDC requires selecting Binary Reader on the source endpoint. Binary Reader requires a supported modern RDS Oracle version, prepared ONLINELOG_DIR and ARCHIVELOG_DIR directories with read grants, and DBA_DIRECTORIES access; RDS TDE-encrypted tablespaces are unsupported with Binary Reader. Verify all Oracle CDC object identifiers, including columns and constraints, fit 30 bytes. Test endpoint connectivity before starting a separate replication_task. PostgreSQL CDC requires logical replication and SQL replication grants; CDC-only also needs an inactive slot, its matching plugin, and a retained WAL start position. The deployment identity needs iam:GetRole, iam:PassRole and secretsmanager:DescribeSecret.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        model = (
            DmsSecretSourceEndpointConfig
            if self._endpoint_type == "source"
            else DmsSecretEndpointConfig
        )
        config = model.model_validate(connection.connection_config)
        database = self._find_instance(connection.target_name, project)
        engine_settings = DMS_SECRET_ENGINES[database.service_type].get(
            database.config.engine
        )
        if engine_settings is None:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("dms",),
                        "msg": "DMS secret endpoints require supported RDS/Aurora MySQL, MariaDB, PostgreSQL, or RDS SQL Server Enterprise/Standard, or RDS Oracle Enterprise/Standard Edition 2 engines",
                    }
                ],
            )
        if (
            isinstance(config, DmsSecretSourceEndpointConfig)
            and (config.postgres_slot_name or config.postgres_plugin_name)
            and database.config.engine not in {"postgres", "aurora-postgresql"}
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("dms",),
                        "msg": "PostgreSQL slot and plugin settings require a PostgreSQL source",
                    }
                ],
            )
        if (
            isinstance(config, DmsSecretSourceEndpointConfig)
            and config.oracle_cdc_reader
            and engine_settings.engine_name != "oracle"
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("oracle_cdc_reader",),
                        "msg": "Oracle CDC reader settings require an Oracle source",
                    }
                ],
            )
        validate_endpoint_identity(connection, project, config.endpoint_id)
        source, target = connection.source_name, connection.target_name
        identifier = dms_identifier("endpoint", config.endpoint_id)
        resource = f"{'aws_rds_cluster' if database.service_type == ServiceType.AURORA else 'aws_db_instance'}.{target}"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source,
                    name=f"dms_database_{target}_engine",
                    value=f"module.{target}.iam_database_engine",
                )
            ],
            outputs=[
                self._output(target, "iam_database_engine", f"{resource}.engine"),
                self._output(
                    source,
                    f"{identifier}_arn",
                    f"aws_dms_endpoint.{identifier}.endpoint_arn",
                    f"DMS {self._endpoint_type} endpoint {config.endpoint_id}",
                ),
            ],
            resources=[
                self._resource(
                    source,
                    f"{identifier}.tf",
                    render_secret_endpoint(
                        config,
                        self._endpoint_type,
                        database.config.engine,
                        identifier,
                        source,
                        target,
                        engine_settings,
                    ),
                )
            ],
        )
