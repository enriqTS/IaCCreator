"""Keep table selection explicit while transforming destination names."""

from app.models.connection_configs.dms_task import DmsReplicationTaskConfig


def table_mapping_rules(config: DmsReplicationTaskConfig) -> list[dict]:
    rules = [
        {
            "rule-type": "selection",
            "rule-id": str(index),
            "rule-name": str(index),
            "rule-action": "explicit",
            "object-locator": {
                "schema-name": config.table_schema,
                "table-name": table,
                "table-type": "table",
            },
        }
        for index, table in enumerate(config.table_names.split(","), start=1)
    ]
    if config.target_schema and config.target_schema != config.table_schema:
        rules.append(
            {
                "rule-type": "transformation",
                "rule-id": str(len(rules) + 1),
                "rule-name": str(len(rules) + 1),
                "rule-action": "rename",
                "rule-target": "schema",
                "object-locator": {"schema-name": config.table_schema},
                "value": config.target_schema,
            }
        )
    if config.target_table_prefix:
        rules.append(
            {
                "rule-type": "transformation",
                "rule-id": str(len(rules) + 1),
                "rule-name": str(len(rules) + 1),
                "rule-action": "add-prefix",
                "rule-target": "table",
                "object-locator": {
                    "schema-name": config.table_schema,
                    "table-name": "%",
                },
                "value": config.target_table_prefix,
            }
        )
    return rules
