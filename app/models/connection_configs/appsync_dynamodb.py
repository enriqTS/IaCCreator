"""GraphQL field and item operation for an AppSync DynamoDB resolver."""

from typing import Literal

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule, VisibleWhen

_GRAPHQL_NAME = ValidationRule(pattern=r"^[_A-Za-z][_0-9A-Za-z]*$")


class AppSyncDynamoDbConfig(BaseConnectionConfig):
    operation: Literal["get_item", "put_item", "update_item", "delete_item"] = (
        ConnectionField(
            "get_item",
            label="Item operation",
            type="select",
            options=[
                OptionEntry(value="get_item", label="Get item"),
                OptionEntry(value="put_item", label="Put item"),
                OptionEntry(value="update_item", label="Update item"),
                OptionEntry(value="delete_item", label="Delete item"),
            ],
        )
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
    hash_argument: str | None = ConnectionField(
        None,
        label="Partition-key argument",
        description="Defaults to the DynamoDB table's partition-key attribute name",
        validation=_GRAPHQL_NAME,
    )
    range_argument: str | None = ConnectionField(
        None,
        label="Sort-key argument",
        description="Defaults to the table's sort-key attribute name when present",
        validation=_GRAPHQL_NAME,
    )
    item_argument: str = ConnectionField(
        "input",
        label="Item argument",
        description="GraphQL argument containing item attributes for PutItem",
        validation=_GRAPHQL_NAME,
        visible_when=VisibleWhen(field="operation", equals="put_item"),
    )
    update_attribute: str | None = ConnectionField(
        None,
        label="Attribute to update",
        description="Required for UpdateItem; replaces this non-key attribute",
        visible_when=VisibleWhen(field="operation", equals="update_item"),
    )
    value_argument: str = ConnectionField(
        "value",
        label="New-value argument",
        description="GraphQL argument containing the replacement value",
        validation=_GRAPHQL_NAME,
        visible_when=VisibleWhen(field="operation", equals="update_item"),
    )
    consistent_read: bool = ConnectionField(
        False,
        label="Consistent read",
        description="Use a strongly consistent GetItem read",
        type="boolean",
        visible_when=VisibleWhen(field="operation", equals="get_item"),
    )
    overwrite: bool = ConnectionField(
        False,
        label="Overwrite existing item",
        description="Allow PutItem to replace an existing item with the same key",
        type="boolean",
        visible_when=VisibleWhen(field="operation", equals="put_item"),
    )

    @property
    def resolved_type_name(self) -> str:
        return self.type_name or (
            "Query" if self.operation == "get_item" else "Mutation"
        )

    @model_validator(mode="after")
    def validate_operation(self):
        names = (
            self.type_name,
            self.field_name,
            self.hash_argument,
            self.range_argument,
            self.item_argument,
            self.value_argument,
        )
        if any(name is not None and name.startswith("__") for name in names):
            raise ValueError(
                "GraphQL introspection names starting with __ are reserved"
            )
        if self.operation == "update_item":
            if not self.update_attribute or not self.update_attribute.strip():
                raise ValueError("UpdateItem requires an attribute to update")
        elif self.update_attribute is not None:
            raise ValueError("Update attribute applies only to UpdateItem")
        if self.operation != "get_item" and self.consistent_read:
            raise ValueError("Consistent reads apply only to GetItem")
        if self.operation != "put_item" and self.overwrite:
            raise ValueError("Overwrite applies only to PutItem")
        return self
