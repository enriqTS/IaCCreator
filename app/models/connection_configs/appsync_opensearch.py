"""GraphQL field and index operation for an AppSync OpenSearch resolver."""

from typing import Literal

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule, VisibleWhen

_GRAPHQL_NAME = ValidationRule(pattern=r"^[_A-Za-z][_0-9A-Za-z]*$")
_INDEX_NAME = ValidationRule(pattern=r"^[a-z0-9][a-z0-9_.-]{0,254}$")


class AppSyncOpenSearchConfig(BaseConnectionConfig):
    operation: Literal[
        "get_document", "search", "index_document", "delete_document"
    ] = ConnectionField(
        "search",
        label="Document operation",
        type="select",
        options=[
            OptionEntry(value="get_document", label="Get document"),
            OptionEntry(value="search", label="Search documents"),
            OptionEntry(value="index_document", label="Index document"),
            OptionEntry(value="delete_document", label="Delete document"),
        ],
    )
    index_name: str = ConnectionField(
        ...,
        label="Index name",
        description="Explicit lowercase index name; wildcards and index lists are not supported",
        validation=_INDEX_NAME,
    )
    type_name: str | None = ConnectionField(
        None,
        label="GraphQL type",
        description="Defaults to Query for reads and Mutation for writes",
        validation=_GRAPHQL_NAME,
    )
    field_name: str = ConnectionField(
        ...,
        label="GraphQL field",
        description="Field on the selected GraphQL type",
        validation=_GRAPHQL_NAME,
    )
    id_argument: str = ConnectionField(
        "id",
        label="Document ID argument",
        description="GraphQL ID argument; accepts letters, digits, underscores, and hyphens",
        validation=_GRAPHQL_NAME,
    )
    query_argument: str = ConnectionField(
        "query",
        label="Search query argument",
        description="GraphQL string argument for a simple query string search",
        validation=_GRAPHQL_NAME,
        visible_when=VisibleWhen(field="operation", equals="search"),
    )
    document_argument: str = ConnectionField(
        "input",
        label="Document argument",
        description="GraphQL input object containing the document to index",
        validation=_GRAPHQL_NAME,
        visible_when=VisibleWhen(field="operation", equals="index_document"),
    )

    @property
    def resolved_type_name(self) -> str:
        return self.type_name or (
            "Query" if self.operation in {"get_document", "search"} else "Mutation"
        )

    @model_validator(mode="after")
    def validate_names(self):
        if any(
            name is not None and name.startswith("__")
            for name in (
                self.type_name,
                self.field_name,
                self.id_argument,
                self.query_argument,
                self.document_argument,
            )
        ):
            raise ValueError(
                "GraphQL introspection names starting with __ are reserved"
            )
        return self
