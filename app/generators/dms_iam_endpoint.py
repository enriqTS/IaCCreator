"""Render an IAM-authenticated DMS endpoint and its dedicated database login role."""

from typing import Literal

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.dms import DmsIamEndpointConfig

DMS_IAM_ENGINES = {
    "mysql": ("mysql", "mysql_settings"),
    "mariadb": ("mariadb", "mysql_settings"),
    "postgres": ("postgres", "postgres_settings"),
    "aurora-mysql": ("aurora", "mysql_settings"),
    "aurora-postgresql": ("aurora-postgresql", "postgres_settings"),
}


def render_iam_endpoint(
    config: DmsIamEndpointConfig,
    endpoint_type: Literal["source", "target"],
    engine: str,
    identifier: str,
    instance_name: str,
    database_module: str,
) -> str:
    renderer = HCLRenderer()
    prefix = f"var.dms_database_{database_module}"
    engine_name, settings = DMS_IAM_ENGINES[engine]
    role = f"aws_iam_role.{identifier}"
    parts = [
        renderer.render_resource(
            "aws_iam_role",
            identifier,
            {
                "name_prefix": f"dms-db-{identifier[-16:]}-",
                "assume_role_policy": renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": "sts:AssumeRole",
                                "Principal": {
                                    "Service": Expr(
                                        'format("dms.%s", data.aws_partition.dms_endpoints.dns_suffix)'
                                    )
                                },
                            }
                        ],
                    }
                ),
            },
        )
    ]
    parts.append(
        renderer.render_resource(
            "aws_iam_role_policy",
            identifier,
            {
                "name": "database-login",
                "role": Expr(f"{role}.id"),
                "policy": renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["rds-db:connect"],
                                "Resource": [
                                    Expr(
                                        f'format("%s/{config.database_user}", {prefix}_iam_resource_arn)'
                                    )
                                ],
                            }
                        ],
                    }
                ),
            },
        )
    )
    certificate = renderer.render_expression(config.certificate_arn)
    parts.append(
        renderer.render_resource(
            "aws_dms_endpoint",
            identifier,
            {
                "endpoint_id": config.endpoint_id,
                "endpoint_type": endpoint_type,
                "engine_name": engine_name,
                "database_name": config.database_name,
                "username": config.database_user,
                "server_name": Expr(f"{prefix}_host"),
                "port": Expr(f"tonumber({prefix}_port)"),
                "ssl_mode": "verify-ca",
                "certificate_arn": config.certificate_arn,
                settings: {
                    "authentication_method": "iam",
                    "service_access_role_arn": Expr(f"{role}.arn"),
                },
                "depends_on": Expr(f"[aws_iam_role_policy.{identifier}]"),
                "lifecycle": {
                    "precondition": [
                        {
                            "condition": Expr(
                                f"{prefix}_engine == {renderer.render_expression(engine)}"
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
            },
        )
    )
    return "\n".join(parts)
