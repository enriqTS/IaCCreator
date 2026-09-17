"""Validate source-specific CDC positions and exclusive named slot use."""

import re
from typing import NoReturn

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms_cdc import (
    CDC_SOURCE_POLICIES,
    POSTGRES_CDC,
    DmsCdcPolicy,
)
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR


def validate_cdc_source(
    connection: ConnectionIR,
    source: ConnectionIR,
    config: DmsReplicationTaskConfig,
    engine: str,
    project: ProjectIR,
    replication_version: str | None,
) -> DmsCdcPolicy | None:
    if config.migration_type == "full-load":
        return None
    policy = CDC_SOURCE_POLICIES.get(engine)
    if policy is None:
        _reject(
            connection,
            "CDC sources must use supported MySQL, PostgreSQL, or SQL Server engines",
        )
    if policy.requires_secret and source.connection_type != "source_secret_endpoint":
        _reject(
            connection,
            f"{policy.label} IAM replication is unsupported; use a Secrets Manager source endpoint",
        )
    if policy.version_pattern and (
        replication_version is None
        or not re.fullmatch(policy.version_pattern, replication_version)
    ):
        _reject(
            connection,
            f"Select DMS replication engine {policy.minimum_version} or newer for {policy.label} CDC",
        )
    if config.cdc_start_position and not re.fullmatch(
        policy.position_pattern, config.cdc_start_position
    ):
        _reject(
            connection, f"{policy.label} CDC requires {policy.position_description}"
        )
    if policy is POSTGRES_CDC:
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
        _validate_slot_consumers(connection, source, project)
    return policy


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


def _reject(connection: ConnectionIR, message: str) -> NoReturn:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": ("dms_task",), "msg": message}],
    )
