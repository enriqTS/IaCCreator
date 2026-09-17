"""Render stopped migration tasks referencing managed DMS endpoints."""

from app.generators.dms_identifiers import dms_identifier
from app.generators.dms_table_mappings import table_mapping_rules
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.dms_cdc import DmsCdcPolicy
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig


def render_replication_task(
    config: DmsReplicationTaskConfig,
    instance: str,
    source_database: str,
    cdc_policy: DmsCdcPolicy | None,
) -> str:
    renderer = HCLRenderer()
    rules = table_mapping_rules(config)
    attrs = {
        "replication_task_id": config.task_id,
        "migration_type": config.migration_type,
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
    }
    if config.migration_type != "cdc":
        attrs["replication_task_settings"] = renderer.render_json_policy(
            {"FullLoadSettings": {"TargetTablePrepMode": "DO_NOTHING"}}
        )
    if config.cdc_start_position is not None:
        attrs["cdc_start_position"] = config.cdc_start_position
    if cdc_policy is not None:
        engines = ", ".join(
            renderer.render_expression(engine) for engine in cdc_policy.engines
        )
        attrs["lifecycle"] = {
            "precondition": [
                {
                    "condition": Expr(
                        f"contains([{engines}], var.dms_database_{source_database}_engine)"
                    ),
                    "error_message": "CDC source engine overrides must match the selected native start-position format and authentication method.",
                }
            ]
        }
        if cdc_policy.version_pattern:
            attrs["lifecycle"]["precondition"].append(
                {
                    "condition": Expr(
                        f"can(regex({renderer.render_expression(cdc_policy.version_pattern)}, aws_dms_replication_instance.{instance}.engine_version))"
                    ),
                    "error_message": f"{cdc_policy.label} CDC requires DMS {cdc_policy.minimum_version} or newer for transaction-log backup access.",
                }
            )
    return renderer.render_resource(
        "aws_dms_replication_task", dms_identifier("task", config.task_id), attrs
    )
