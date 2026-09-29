"""AppSync JavaScript resolver for publishing one EventBridge event."""

import json

from app.models.connection_configs.appsync_eventbridge import AppSyncEventBridgeConfig


def eventbridge_resolver_code(config: AppSyncEventBridgeConfig) -> str:
    return (
        "import { util } from '@aws-appsync/utils';\n"
        "export function request(ctx) {\n"
        "  return { operation: 'PutEvents', events: [{\n"
        f"    source: {json.dumps(config.event_source)},\n"
        f"    detailType: {json.dumps(config.detail_type)},\n"
        f"    detail: ctx.args[{json.dumps(config.detail_argument)}],\n"
        "  }] };\n"
        "}\n"
        "export function response(ctx) {\n"
        "  if (ctx.error) util.error(ctx.error.message, ctx.error.type);\n"
        "  const entry = ctx.result.Entries && ctx.result.Entries[0];\n"
        "  if (ctx.result.FailedEntryCount > 0 || !entry || !entry.EventId) {\n"
        "    util.error(entry?.ErrorMessage || 'EventBridge did not accept the event',\n"
        "      entry?.ErrorCode || 'EventBridgePutEventsFailed');\n"
        "  }\n"
        "  return entry.EventId;\n"
        "}\n"
    )
