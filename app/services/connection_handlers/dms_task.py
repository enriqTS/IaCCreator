"""Resolve task endpoint relationships before emitting DMS-owned resources."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.dms_identifiers import dms_identifier
from app.generators.dms_replication_task import render_replication_task
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.dms_cdc import validate_cdc_source


class DmsReplicationTaskHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Creates a stopped migration task for explicitly selected tables. Full-load modes use DO_NOTHING target preparation and need compatible target schemas and empty tables. Verify SQL permissions, deploy and test both endpoint connections before applying the task, then start it separately. Optional schema renaming and table prefixes affect only selected tables; prepare the resulting destination names before loading. Changes to transformations require a task restart rather than resume. For MySQL CDC, configure ROW binlogging with FULL row images, sufficient log retention/backups, and replication SQL grants on the source. CDC-only targets must already contain data consistent with the chosen binlog position. PostgreSQL CDC requires a Secrets Manager source, logical replication, sufficient WAL retention/slots/senders, and replication SQL grants. For PostgreSQL sources, CDC-only targets must match the selected LSN and inactive slot; select the slot plugin explicitly. Verify primary keys or replica identity and DDL capture prerequisites. SQL Server CDC requires DMS 3.5.3 or newer, MS-CDC enabled on the RDS database and every selected table, transaction-log retention and backup access, and replication SQL grants. CDC-only targets must match the selected SQL Server LSN. Non-CDB Oracle CDC uses LogMiner with a Secrets Manager source, supplemental logging, retained archive logs, and SQL grants. CDC-only requires an Oracle SCN covering the earliest open transaction and matching the target snapshot. CDB/PDB CDC requires Binary Reader and is not implemented. Schema conversion, column transformations, task logging, and automatic migration execution are not configured. Terraform manages start_replication_task=false; a later apply can stop a task started externally.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = DmsReplicationTaskConfig.model_validate(connection.connection_config)
        endpoints = []
        for kind, endpoint_id in (
            ("source_endpoint", config.source_endpoint_id),
            ("target_endpoint", config.target_endpoint_id),
        ):
            matches = [
                other
                for other in project.connections
                if other.source_service == ServiceType.DATABASE_MIGRATION_SERVICE
                and other.source_name == connection.source_name
                and other.connection_type
                in {kind, kind.replace("_endpoint", "_secret_endpoint")}
                and other.connection_config.get("endpoint_id") == endpoint_id
            ]
            if not matches:
                self._reject(
                    connection,
                    f"Task requires a {kind} connection named {endpoint_id} on this DMS instance",
                )
            endpoints.append(matches[0])
        source, target = endpoints
        database = self._find_instance(source.target_name, project)
        instance = self._find_instance(connection.source_name, project)
        cdc_policy = validate_cdc_source(
            connection,
            source,
            config,
            database.config.engine,
            project,
            instance.config.engine_version,
        )
        if target.target_name != connection.target_name:
            self._reject(
                connection,
                "The task target endpoint must connect to this task's target database",
            )
        if (
            source.target_name == target.target_name
            and source.connection_config["database_name"]
            == target.connection_config["database_name"]
        ):
            self._reject(
                connection,
                "Migration source and target must select different databases",
            )
        for other in project.connections:
            if (
                other.source_service == ServiceType.DATABASE_MIGRATION_SERVICE
                and other.connection_type == "replication_task"
                and other.connection_config.get("task_id") == config.task_id
                and (other.source_name, other.target_name, other.connection_config)
                != (
                    connection.source_name,
                    connection.target_name,
                    connection.connection_config,
                )
            ):
                self._reject(
                    connection,
                    "DMS task identifiers must be unique across this project",
                )
        identifier = dms_identifier("task", config.task_id)
        owner = connection.source_name
        return ConnectionContribution(
            resources=[
                self._resource(
                    owner,
                    f"{identifier}.tf",
                    render_replication_task(
                        config, owner, source.target_name, cdc_policy
                    ),
                )
            ],
            outputs=[
                self._output(
                    owner,
                    f"{identifier}_arn",
                    f"aws_dms_replication_task.{identifier}.replication_task_arn",
                    f"DMS {config.migration_type} task {config.task_id}",
                )
            ],
        )

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("dms_task",), "msg": message}],
        )
