"""AppSync JavaScript resolvers for parameterized Aurora PostgreSQL row operations."""

import json

from app.models.connection_configs.appsync_aurora import AppSyncAuroraConfig


def aurora_resolver_code(config: AppSyncAuroraConfig) -> str:
    table = json.dumps(config.table_name)
    column = json.dumps(config.id_column)
    identifier = f"ctx.args[{json.dumps(config.id_argument)}]"
    values = f"ctx.args[{json.dumps(config.input_argument)}]"
    where = f"{{ {column}: {{ eq: {identifier} }} }}"
    if config.operation == "get_row":
        statement = f"select({{ table: {table}, where: {where}, limit: 1 }})"
    elif config.operation == "list_rows":
        statement = f"select({{ table: {table}, limit: 50 }})"
    elif config.operation == "insert_row":
        statement = f"insert({{ table: {table}, values: {values}, returning: '*' }})"
    elif config.operation == "update_row":
        statement = (
            f"update({{ table: {table}, values, where: {where}, returning: '*' }})"
        )
    else:
        statement = f"remove({{ table: {table}, where: {where}, returning: '*' }})"
    setup = ""
    if config.operation == "update_row":
        setup = (
            f"  const values = {{ ...{values} }};\n"
            f"  delete values[{column}];\n"
            "  if (Object.keys(values).length === 0) util.error('No columns to update', 'BadRequest');\n"
        )
    response = (
        "  return toJsonObject(ctx.result)?.[0] || [];\n"
        if config.operation == "list_rows"
        else "  return toJsonObject(ctx.result)?.[0]?.[0] || null;\n"
    )
    imports = (
        "import { createPgStatement, toJsonObject, select, insert, update, remove } "
        "from '@aws-appsync/utils/rds';\n"
    )
    return (
        "import { util } from '@aws-appsync/utils';\n"
        + imports
        + "export function request(ctx) {\n"
        + setup
        + f"  return createPgStatement({statement});\n"
        + "}\n"
        + "export function response(ctx) {\n"
        + "  if (ctx.error) util.error(ctx.error.message, ctx.error.type);\n"
        + response
        + "}\n"
    )
