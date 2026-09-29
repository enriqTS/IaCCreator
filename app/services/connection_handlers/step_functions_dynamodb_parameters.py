"""Optimized DynamoDB operation names and workflow task parameters."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.step_functions_dynamodb import (
    StepFunctionsDynamoDbConfig,
)

OPERATIONS = {
    "get_item": "getItem",
    "put_item": "putItem",
    "update_item": "updateItem",
    "delete_item": "deleteItem",
}


def dynamodb_task_parameters(
    config: StepFunctionsDynamoDbConfig, table_variable: str
) -> dict:
    parameters = {"TableName": Expr(f"var.{table_variable}")}
    if config.operation == "put_item":
        parameters["Item.$"] = config.item_path
    else:
        parameters["Key.$"] = config.key_path
    if config.operation == "get_item" and config.consistent_read:
        parameters["ConsistentRead"] = True
    if config.operation == "update_item":
        parameters["UpdateExpression"] = config.update_expression
    if config.condition_expression:
        parameters["ConditionExpression"] = config.condition_expression
    if config.expression_attribute_names_path:
        parameters["ExpressionAttributeNames.$"] = (
            config.expression_attribute_names_path
        )
    if config.expression_attribute_values_path:
        parameters["ExpressionAttributeValues.$"] = (
            config.expression_attribute_values_path
        )
    return parameters
