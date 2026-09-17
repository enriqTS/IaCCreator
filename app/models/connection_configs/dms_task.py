"""Typed migration modes, start positions, and explicit table selections."""

import re
from typing import Literal

from pydantic import field_validator, model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.dms import DmsEndpointConfig
from app.models.connection_configs.dms_positions import (
    MYSQL_POSITION_PATTERN,
    POSTGRES_POSITION_PATTERN,
    SQLSERVER_POSITION_PATTERN,
)
from app.models.input_models._metadata import OptionEntry, ValidationRule, VisibleWhen


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

    migration_type: Literal["full-load", "full-load-and-cdc", "cdc"] = ConnectionField(
        "full-load",
        label="Migration mode",
        type="select",
        options=[
            OptionEntry(value="full-load", label="Full load"),
            OptionEntry(
                value="full-load-and-cdc", label="Full load and ongoing changes"
            ),
            OptionEntry(value="cdc", label="Ongoing changes only"),
        ],
    )
    cdc_start_position: str | None = ConnectionField(
        None,
        label="CDC native start position",
        description="Required for CDC-only tasks; use the source engine's binlog position or PostgreSQL/SQL Server LSN matching the existing target snapshot",
        placeholder="mysql-bin-changelog.000024:373",
        visible_when=VisibleWhen(field="migration_type", equals="cdc"),
        validation=ValidationRule(
            pattern=rf"^(?:{MYSQL_POSITION_PATTERN}|{POSTGRES_POSITION_PATTERN}|{SQLSERVER_POSITION_PATTERN})$"
        ),
    )

    target_schema: str | None = ConnectionField(
        None,
        label="Target schema (optional)",
        description="Rename the selected source schema in the destination",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$"),
    )
    target_table_prefix: str | None = ConnectionField(
        None,
        label="Target table prefix (optional)",
        description="Prefix applied to every selected destination table",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,61}$"),
    )

    @field_validator(
        "target_schema", "target_table_prefix", "cdc_start_position", mode="before"
    )
    @classmethod
    def normalize_optional_name(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_cdc_position(self):
        if self.migration_type == "cdc" and not self.cdc_start_position:
            raise ValueError("CDC-only tasks require an explicit native start position")
        if self.migration_type != "cdc" and self.cdc_start_position is not None:
            raise ValueError(
                "A native start position is only supported for CDC-only tasks"
            )
        return self

    @model_validator(mode="after")
    def validate_target_names(self):
        prefix = self.target_table_prefix or ""
        if any(len(prefix + table) > 63 for table in self.table_names.split(",")):
            raise ValueError(
                "Target table names including the prefix must not exceed 63 characters"
            )
        return self

    @field_validator("task_id", "source_endpoint_id", "target_endpoint_id")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return DmsEndpointConfig.normalize_endpoint_id(value)

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
