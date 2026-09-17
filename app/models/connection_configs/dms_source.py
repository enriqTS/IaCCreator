"""Source settings select database-specific CDC readers and replication slots."""

from typing import Literal

from pydantic import field_validator, model_validator

from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.dms import DmsSecretEndpointConfig
from app.models.input_models._metadata import OptionEntry, ValidationRule


class DmsSecretSourceEndpointConfig(DmsSecretEndpointConfig):
    oracle_cdc_reader: Literal["logminer", "binary-reader"] | None = ConnectionField(
        None,
        label="Oracle CDC reader (optional)",
        description="Binary Reader is required for PDB CDC; this profile requires RDS Oracle 12.2, 18, or 19 with prepared log directories and grants",
        type="select",
        options=[
            OptionEntry(value="logminer", label="LogMiner (non-CDB only)"),
            OptionEntry(
                value="binary-reader", label="Binary Reader (modern RDS Oracle)"
            ),
        ],
    )
    postgres_slot_name: str | None = ConnectionField(
        None,
        label="PostgreSQL replication slot (optional)",
        description="Existing inactive logical slot; required for PostgreSQL CDC-only tasks",
        validation=ValidationRule(pattern=r"^[a-z0-9_]{1,63}$"),
    )
    postgres_plugin_name: Literal["test-decoding", "pglogical"] | None = (
        ConnectionField(
            None,
            label="PostgreSQL decoding plugin (optional)",
            description="Must match an existing slot; omit to use DMS defaults when creating a slot",
            type="select",
            options=[
                OptionEntry(value="test-decoding", label="test_decoding"),
                OptionEntry(value="pglogical", label="pglogical"),
            ],
        )
    )

    @field_validator(
        "postgres_slot_name", "postgres_plugin_name", "oracle_cdc_reader", mode="before"
    )
    @classmethod
    def normalize_optional_settings(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_slot_plugin(self):
        if self.postgres_slot_name and not self.postgres_plugin_name:
            raise ValueError(
                "Select the decoding plugin of the existing PostgreSQL slot"
            )
        return self
