"""Validate source-specific CDC positions and exclusive named slot use."""

import re

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms_positions import (
    MYSQL_POSITION_PATTERN,
    POSTGRES_POSITION_PATTERN,
)
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR

MYSQL_ENGINES = ("mysql", "mariadb", "aurora-mysql")
POSTGRES_ENGINES = ("postgres", "aurora-postgresql")


def validate_cdc_source(
    connection: ConnectionIR,
    source: ConnectionIR,
    config: DmsReplicationTaskConfig,
    engine: str,
    project: ProjectIR,
) -> tuple[str, ...]:
    if config.migration_type == "full-load":
        return ()
    if engine in POSTGRES_ENGINES:
        if source.connection_type != "source_secret_endpoint":
            _reject(
                connection,
                "PostgreSQL IAM replication is unsupported; use a Secrets Manager source endpoint",
            )
        if (
            config.migration_type == "full-load-and-cdc"
            and source.connection_config.get("postgres_slot_name")
        ):
            _reject(
                connection,
                "Named PostgreSQL slots are supported here only for CDC-only tasks",
            )
        if config.migration_type == "cdc" and not source.connection_config.get(
            "postgres_slot_name"
        ):
            _reject(
                connection,
                "PostgreSQL CDC-only tasks require an existing logical replication slot on the source endpoint",
            )
        if config.cdc_start_position and not re.fullmatch(
            POSTGRES_POSITION_PATTERN, config.cdc_start_position
        ):
            _reject(
                connection,
                "PostgreSQL CDC requires a native WAL LSN such as 4AF/B00000D0",
            )
        _validate_slot_consumers(connection, source, project)
        return POSTGRES_ENGINES
    if engine not in MYSQL_ENGINES:
        _reject(
            connection, "CDC sources must use supported MySQL or PostgreSQL engines"
        )
    if config.cdc_start_position and not re.fullmatch(
        MYSQL_POSITION_PATTERN, config.cdc_start_position
    ):
        _reject(connection, "MySQL CDC requires a native binlog filename and position")
    return MYSQL_ENGINES


def _validate_slot_consumers(
    connection: ConnectionIR, source: ConnectionIR, project: ProjectIR
) -> None:
    slot = source.connection_config.get("postgres_slot_name")
    if not slot:
        return
    endpoints = {
        (endpoint.source_name, endpoint.connection_config.get("endpoint_id")): endpoint
        for endpoint in project.connections
        if endpoint.source_service == ServiceType.DATABASE_MIGRATION_SERVICE
        and endpoint.connection_type == "source_secret_endpoint"
    }
    for other in project.connections:
        if (
            other.source_service != ServiceType.DATABASE_MIGRATION_SERVICE
            or other.connection_type != "replication_task"
            or other.connection_config.get("migration_type", "full-load") == "full-load"
            or (other.source_name, other.connection_config.get("task_id"))
            == (connection.source_name, connection.connection_config.get("task_id"))
        ):
            continue
        endpoint = endpoints.get(
            (other.source_name, other.connection_config.get("source_endpoint_id"))
        )
        if (
            endpoint
            and endpoint.target_name == source.target_name
            and endpoint.connection_config.get("postgres_slot_name") == slot
        ):
            _reject(
                connection,
                "A named PostgreSQL replication slot cannot be shared by multiple CDC tasks",
            )


def _reject(connection: ConnectionIR, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": ("dms_task",), "msg": message}],
    )
