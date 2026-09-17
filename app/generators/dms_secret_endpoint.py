"""Render secret references without loading credentials into Terraform."""

from typing import Literal

from app.generators.dms_secret_engines import DmsSecretEngine
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.dms import DmsSecretEndpointConfig
from app.models.connection_configs.dms_source import DmsSecretSourceEndpointConfig


def render_secret_endpoint(
    config: DmsSecretEndpointConfig,
    endpoint_type: Literal["source", "target"],
    engine: str,
    identifier: str,
    instance_name: str,
    database_module: str,
    engine_settings: DmsSecretEngine,
) -> str:
    renderer = HCLRenderer()
    certificate = renderer.render_expression(config.certificate_arn)
    attrs = {
        "endpoint_id": config.endpoint_id,
        "endpoint_type": endpoint_type,
        "engine_name": engine_settings.engine_name,
        "database_name": config.database_name,
        "secrets_manager_arn": config.secrets_manager_arn,
        "secrets_manager_access_role_arn": config.secrets_manager_access_role_arn,
        "ssl_mode": engine_settings.ssl_mode,
        "certificate_arn": config.certificate_arn,
        "lifecycle": {
            "precondition": [
                {
                    "condition": Expr(
                        f"var.dms_database_{database_module}_engine == {renderer.render_expression(engine)}"
                    ),
                    "error_message": "Database engine overrides must match the generated DMS endpoint settings.",
                },
                {
                    "condition": Expr(
                        f'join(":", slice(split(":", {certificate}), 0, 5)) == join(":", slice(split(":", aws_dms_replication_instance.{instance_name}.replication_instance_arn), 0, 5))'
                    ),
                    "error_message": "Import the DMS CA certificate in the replication instance account and Region.",
                },
            ]
        },
    }
    if isinstance(config, DmsSecretSourceEndpointConfig):
        settings = {
            key: value
            for key, value in {
                "slot_name": config.postgres_slot_name,
                "plugin_name": config.postgres_plugin_name,
            }.items()
            if value is not None
        }
        if settings:
            settings["capture_ddls"] = True
            attrs["postgres_settings"] = settings
    return renderer.render_resource("aws_dms_endpoint", identifier, attrs)
