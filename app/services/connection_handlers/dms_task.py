"""Resolve task endpoint relationships before emitting DMS-owned resources."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.dms_identifiers import dms_identifier
from app.generators.dms_replication_task import render_replication_task
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


class DmsReplicationTaskHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Creates a stopped migration task for explicitly selected tables. Full-load modes use DO_NOTHING target preparation and need compatible target schemas and empty tables. Verify SQL permissions, deploy and test both endpoint connections before applying the task, then start it separately. Optional schema renaming and table prefixes affect only selected tables; prepare the resulting destination names before loading. Changes to transformations require a task restart rather than resume. For CDC, configure ROW binlogging with FULL row images, sufficient log retention/backups, and replication SQL grants on the source. CDC-only targets must already contain data consistent with the chosen binlog position. PostgreSQL IAM sources only support full load. Schema conversion, column transformations, task logging, and automatic migration execution are not configured. Terraform manages start_replication_task=false; a later apply can stop a task started externally.",
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
                and other.connection_type == kind
                and other.connection_config.get("endpoint_id") == endpoint_id
            ]
            if not matches:
                self._reject(
                    connection,
                    f"Task requires a {kind} connection named {endpoint_id} on this DMS instance",
                )
            endpoints.append(matches[0])
        source, target = endpoints
        if config.migration_type != "full-load":
            database = self._find_instance(source.target_name, project)
            if database.config.engine not in {"mysql", "mariadb", "aurora-mysql"}:
                self._reject(
                    connection,
                    "IAM-authenticated CDC sources must use MySQL, MariaDB, or Aurora MySQL; PostgreSQL IAM replication is unsupported",
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
                    render_replication_task(config, owner, source.target_name),
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
