"""Typed identifiers and explicit table selections for full-load tasks."""

import re

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.dms import DmsIamEndpointConfig
from app.models.input_models._metadata import ValidationRule


class DmsReplicationTaskConfig(BaseConnectionConfig):
    task_id: str = ConnectionField(
        ...,
        label="Replication task identifier",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9-]{0,254}$"),
    )
    source_endpoint_id: str = ConnectionField(
        ...,
        label="Source endpoint identifier",
        description="Existing source endpoint connection on this DMS instance",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9-]{0,254}$"),
    )
    target_endpoint_id: str = ConnectionField(
        ...,
        label="Target endpoint identifier",
        description="Existing target endpoint connection to this database on this DMS instance",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9-]{0,254}$"),
    )
    table_schema: str = ConnectionField(
        ...,
        label="Source schema",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$"),
    )
    table_names: str = ConnectionField(
        ...,
        label="Source tables (comma-separated)",
        description="Explicit table names in the source schema; no wildcards",
        placeholder="customers,orders",
    )

    @field_validator("task_id", "source_endpoint_id", "target_endpoint_id")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return DmsIamEndpointConfig.normalize_endpoint_id(value)

    @field_validator("table_names")
    @classmethod
    def normalize_tables(cls, value: str) -> str:
        names = value.split(",")
        if len(names) > 100 or any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", name.strip())
            for name in names
        ):
            raise ValueError(
                "Select 1–100 explicit table names, each up to 63 characters"
            )
        return ",".join(sorted({name.strip() for name in names}))
