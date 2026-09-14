"""Explicit existing-table selectors prevent database-wide application grants."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class KeyspacesTableAccessConfig(BaseConnectionConfig):
    table_name: str = ConnectionField(
        ...,
        label="Existing table name",
        description="Table provisioned separately in this keyspace",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9][A-Za-z0-9_]{0,47}$"),
    )


class TimestreamTableAccessConfig(BaseConnectionConfig):
    table_name: str = ConnectionField(
        ...,
        label="Existing table name",
        description="Table provisioned separately in this Timestream database",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_.-]{3,256}$"),
    )
