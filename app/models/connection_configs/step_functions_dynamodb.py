"""One DynamoDB item operation bound to a JSONPath workflow state."""

from typing import Literal

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule, VisibleWhen

_PATH = ValidationRule(pattern=r"^\$(?:\.[A-Za-z_][A-Za-z0-9_]*|\[[0-9]+\])*$")


class StepFunctionsDynamoDbConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )
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
    key_path: str = ConnectionField(
        "$.key",
        label="Key path",
        description="JSONPath to a DynamoDB AttributeValue map containing the table's primary key; used by GetItem, UpdateItem, and DeleteItem",
        validation=_PATH,
    )
    item_path: str = ConnectionField(
        "$.item",
        label="Item path",
        description="JSONPath to a DynamoDB AttributeValue map containing the item, including its primary key",
        validation=_PATH,
        visible_when=VisibleWhen(field="operation", equals="put_item"),
    )
    update_expression: str | None = ConnectionField(
        None,
        label="Update expression",
        description="Required for UpdateItem; use expression-attribute paths for placeholders",
        visible_when=VisibleWhen(field="operation", equals="update_item"),
    )
    condition_expression: str | None = ConnectionField(
        None,
        label="Condition expression",
        description="Optional condition for PutItem, UpdateItem, and DeleteItem",
    )
    expression_attribute_names_path: str | None = ConnectionField(
        None,
        label="Expression names path",
        description="JSONPath to a map of #name placeholders for write expressions",
        validation=_PATH,
    )
    expression_attribute_values_path: str | None = ConnectionField(
        None,
        label="Expression values path",
        description="JSONPath to a map of :value placeholders in DynamoDB AttributeValue format",
        validation=_PATH,
    )
    consistent_read: bool = ConnectionField(
        False,
        label="Consistent read",
        description="Use strongly consistent GetItem reads",
        type="boolean",
        visible_when=VisibleWhen(field="operation", equals="get_item"),
    )

    @model_validator(mode="after")
    def validate_operation_fields(self):
        if (
            self.condition_expression is not None
            and not self.condition_expression.strip()
        ):
            raise ValueError("Condition expressions must not be blank")
        if self.operation == "update_item" and not (
            self.update_expression and self.update_expression.strip()
        ):
            raise ValueError("UpdateItem requires an update expression")
        if self.operation != "update_item" and self.update_expression:
            raise ValueError("Update expressions apply only to UpdateItem")
        if self.operation == "get_item" and self.condition_expression:
            raise ValueError("GetItem does not support a condition expression")
        if self.operation != "get_item" and self.consistent_read:
            raise ValueError("Consistent reads apply only to GetItem")
        expressions = " ".join(
            value
            for value in (self.update_expression, self.condition_expression)
            if value
        )
        if not expressions and (
            self.expression_attribute_names_path
            or self.expression_attribute_values_path
        ):
            raise ValueError(
                "Expression paths require an update or condition expression"
            )
        if ":" in expressions and not self.expression_attribute_values_path:
            raise ValueError(
                "Expression values path is required for :value placeholders"
            )
        if "#" in expressions and not self.expression_attribute_names_path:
            raise ValueError("Expression names path is required for #name placeholders")
        return self
