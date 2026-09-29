"""AppSync JavaScript unit resolvers for DynamoDB item operations."""

import json
from collections.abc import Callable

from app.models.connection_configs.appsync_dynamodb import AppSyncDynamoDbConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig


def _key_expression(config: AppSyncDynamoDbConfig, table: DynamoDBConfig) -> str:
    parts = [
        f"{json.dumps(table.hash_key)}: ctx.args[{json.dumps(config.hash_argument or table.hash_key)}]"
    ]
    if table.range_key:
        parts.append(
            f"{json.dumps(table.range_key)}: ctx.args[{json.dumps(config.range_argument or table.range_key)}]"
        )
    return "{ " + ", ".join(parts) + " }"


def _get_item(config: AppSyncDynamoDbConfig, table: DynamoDBConfig) -> str:
    options = "key, consistentRead: true" if config.consistent_read else "key"
    return f"ddb.get({{ {options} }})"


def _put_item(config: AppSyncDynamoDbConfig, table: DynamoDBConfig) -> str:
    item = f"ctx.args[{json.dumps(config.item_argument)}]"
    options = f"key, item: {item}"
    if not config.overwrite:
        options += f", condition: {{ {json.dumps(table.hash_key)}: {{ attributeExists: false }} }}"
    return f"ddb.put({{ {options} }})"


def _update_item(config: AppSyncDynamoDbConfig, table: DynamoDBConfig) -> str:
    attribute = json.dumps(config.update_attribute)
    value = f"ctx.args[{json.dumps(config.value_argument)}]"
    return (
        f"ddb.update({{ key, update: {{ {attribute}: ddb.operations.replace({value}) }}, "
        f"condition: {{ {json.dumps(table.hash_key)}: {{ attributeExists: true }} }} }})"
    )


def _delete_item(config: AppSyncDynamoDbConfig, table: DynamoDBConfig) -> str:
    return "ddb.remove({ key })"


_OPERATIONS: dict[str, Callable[[AppSyncDynamoDbConfig, DynamoDBConfig], str]] = {
    "get_item": _get_item,
    "put_item": _put_item,
    "update_item": _update_item,
    "delete_item": _delete_item,
}


def dynamodb_resolver_code(config: AppSyncDynamoDbConfig, table: DynamoDBConfig) -> str:
    key = _key_expression(config, table)
    request = _OPERATIONS[config.operation](config, table)
    return (
        "import * as ddb from '@aws-appsync/utils/dynamodb';\n"
        "export function request(ctx) {\n"
        f"  const key = {key};\n"
        f"  return {request};\n"
        "}\n"
        "export const response = (ctx) => ctx.result;\n"
    )
