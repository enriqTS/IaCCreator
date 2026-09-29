"""KMS references for AppSync DynamoDB data-source roles."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import (
    ConnectionContribution,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


def table_key_reference(
    api: str, table: str, project: ProjectIR
) -> tuple[ConnectionContribution, Expr | None, str]:
    target = BaseConnectionHandler._find_instance(table, project)
    key = managed_key(table, project)
    external = target.config.server_side_encryption_kms_key_arn
    if key:
        variable = f"appsync_{table}_kms_key_arn"
        return (
            ConnectionContribution(
                inputs=[
                    ModuleInput(
                        module=api,
                        name=variable,
                        value=f"module.{key}.key_arn",
                    )
                ]
            ),
            Expr(f"var.{variable}"),
            "",
        )
    if external and target.config.server_side_encryption_enabled:
        variable = f"appsync_{table}_kms_key_id"
        lookup = f'data "aws_kms_key" "{variable}" {{\n  key_id = var.{variable}\n}}\n'
        return (
            ConnectionContribution(
                outputs=[
                    ModuleOutput(
                        module=table,
                        name="appsync_kms_key_id",
                        value="var.server_side_encryption_kms_key_arn",
                    )
                ],
                inputs=[
                    ModuleInput(
                        module=api,
                        name=variable,
                        value=f"module.{table}.appsync_kms_key_id",
                    )
                ],
            ),
            Expr(f"data.aws_kms_key.{variable}.arn"),
            lookup,
        )
    return ConnectionContribution(), None, ""
