"""Render stopped full-load tasks referencing managed DMS endpoints."""

from app.generators.dms_identifiers import dms_identifier
from app.generators.dms_table_mappings import table_mapping_rules
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig


def render_replication_task(config: DmsReplicationTaskConfig, instance: str) -> str:
    renderer = HCLRenderer()
    rules = table_mapping_rules(config)
    return renderer.render_resource(
        "aws_dms_replication_task",
        dms_identifier("task", config.task_id),
        {
            "replication_task_id": config.task_id,
            "migration_type": "full-load",
            "replication_instance_arn": Expr(
                f"aws_dms_replication_instance.{instance}.replication_instance_arn"
            ),
            "source_endpoint_arn": Expr(
                f"aws_dms_endpoint.{dms_identifier('endpoint', config.source_endpoint_id)}.endpoint_arn"
            ),
            "target_endpoint_arn": Expr(
                f"aws_dms_endpoint.{dms_identifier('endpoint', config.target_endpoint_id)}.endpoint_arn"
            ),
            "start_replication_task": False,
            "table_mappings": renderer.render_json_policy({"rules": rules}),
            "replication_task_settings": renderer.render_json_policy(
                {"FullLoadSettings": {"TargetTablePrepMode": "DO_NOTHING"}}
            ),
        },
    )
