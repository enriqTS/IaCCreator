"""AppSync JavaScript resolvers for index-scoped OpenSearch document operations."""

import json

from app.models.connection_configs.appsync_opensearch import AppSyncOpenSearchConfig


def opensearch_resolver_code(config: AppSyncOpenSearchConfig) -> str:
    path = json.dumps(f"/{config.index_name}")
    if config.operation == "search":
        request = (
            f"  return {{ operation: 'POST', path: {path} + '/_search',\n"
            "    params: { body: { size: 50, query: { simple_query_string: "
            f"{{ query: ctx.args[{json.dumps(config.query_argument)}] }} }} }} }};\n"
        )
        response = "  return ctx.result.hits.hits.map((hit) => hit._source);\n"
    else:
        request = (
            f"  const id = ctx.args[{json.dumps(config.id_argument)}];\n"
            "  if (!util.matches('^[A-Za-z0-9_-]+$', id)) {\n"
            "    util.error('Document ID must contain only letters, digits, underscores, or hyphens', 'BadRequest');\n"
            "  }\n"
        )
        method = {
            "get_document": "GET",
            "index_document": "PUT",
            "delete_document": "DELETE",
        }[config.operation]
        request += (
            f"  return {{ operation: '{method}', "
            f"path: {path} + '/_doc/' + util.urlEncode(id)"
        )
        if config.operation == "index_document":
            request += f", params: {{ body: ctx.args[{json.dumps(config.document_argument)}] }}"
        request += " };\n"
        response = (
            "  return ctx.result._source;\n"
            if config.operation == "get_document"
            else "  return ctx.result;\n"
        )
    return (
        "import { util } from '@aws-appsync/utils';\n"
        "export function request(ctx) {\n" + request + "}\n"
        "export function response(ctx) {\n"
        "  if (ctx.error) util.error(ctx.error.message, ctx.error.type);\n"
        + response
        + "}\n"
    )
