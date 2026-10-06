"""GraphQL field and table operation for an Aurora Data API resolver."""

from typing import Literal

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule

_GRAPHQL_NAME = ValidationRule(pattern=r"^[_A-Za-z][_0-9A-Za-z]*$")
_SQL_NAME = ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
_TABLE_NAME = ValidationRule(
    pattern=r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$"
)
_SECRET_ARN = ValidationRule(
    pattern=r"^arn:[^:]+:secretsmanager:[^:]+:[0-9]{12}:secret:.+$"
)
_KMS_KEY_ARN = ValidationRule(
    pattern=r"^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/[A-Za-z0-9-]+$"
)


class AppSyncAuroraConfig(BaseConnectionConfig):
    operation: Literal[
        "get_row", "list_rows", "insert_row", "update_row", "delete_row"
    ] = ConnectionField(
        "get_row",
        label="SQL operation",
        type="select",
        options=[
            OptionEntry(value="get_row", label="Get row"),
            OptionEntry(value="list_rows", label="List rows"),
            OptionEntry(value="insert_row", label="Insert row"),
            OptionEntry(value="update_row", label="Update row"),
            OptionEntry(value="delete_row", label="Delete row"),
        ],
    )
    field_name: str = ConnectionField(
        ...,
        label="GraphQL field",
        validation=_GRAPHQL_NAME,
    )
    type_name: str | None = ConnectionField(
        None,
        label="GraphQL type",
        description="Defaults to Query for reads and Mutation for writes",
        validation=_GRAPHQL_NAME,
    )
    table_name: str = ConnectionField(
        ...,
        label="SQL table",
        description="Existing table, optionally qualified by a PostgreSQL schema",
        validation=_TABLE_NAME,
    )
    id_column: str = ConnectionField("id", label="Row ID column", validation=_SQL_NAME)
    id_argument: str = ConnectionField(
        "id", label="Row ID argument", validation=_GRAPHQL_NAME
    )
    input_argument: str = ConnectionField(
        "input", label="Row input argument", validation=_GRAPHQL_NAME
    )
    credential_secret_arn: str = ConnectionField(
        ...,
        label="Database-user secret ARN",
        description="Existing Secrets Manager secret for a least-privilege database user",
        validation=_SECRET_ARN,
    )
    credential_kms_key_arn: str | None = ConnectionField(
        None,
        label="Secret KMS key ARN",
        description="Customer-managed KMS key protecting the database-user secret, if any",
        validation=_KMS_KEY_ARN,
    )

    @property
    def resolved_type_name(self) -> str:
        return self.type_name or (
            "Query" if self.operation in {"get_row", "list_rows"} else "Mutation"
        )

    @model_validator(mode="after")
    def validate_names(self):
        if any(
            name is not None and name.startswith("__")
            for name in (
                self.field_name,
                self.type_name,
                self.id_argument,
                self.input_argument,
            )
        ):
            raise ValueError(
                "GraphQL introspection names starting with __ are reserved"
            )
        return self
