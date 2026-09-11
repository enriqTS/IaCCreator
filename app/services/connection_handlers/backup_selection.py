"""Backup plans own selections of managed resources using an external service role."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.backup import BackupSelectionConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler

BACKUP_OUTPUTS = {
    ServiceType.EBS: "volume_arn",
    ServiceType.EFS: "file_system_arn",
    ServiceType.RDS: "db_instance_arn",
    ServiceType.AURORA: "cluster_arn",
    ServiceType.DYNAMODB: "table_arn",
}


class BackupSelectionHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The external backup role must trust backup.amazonaws.com and hold the resource's backup and KMS permissions. This connection selects the resource; it does not create or modify that role or enable account-level backup settings.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        plan, target = connection.source_name, connection.target_name
        config = BackupSelectionConfig.model_validate(connection.connection_config)
        roles = {
            BackupSelectionConfig.model_validate(item.connection_config).role_arn
            for item in project.connections
            if item.source_name == plan
            and item.target_name == target
            and item.connection_type == "backs_up"
        }
        if len(roles) != 1:
            raise InvalidConnectionConfigError(
                plan,
                target,
                connection.connection_type,
                [
                    {
                        "loc": ("role_arn",),
                        "msg": "A plan/resource selection must use one backup service role",
                    }
                ],
            )
        variable = f"backup_{target}_arn"
        role_variable = f"backup_{target}_role_arn"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=plan,
                    name=variable,
                    value=f"module.{target}.{BACKUP_OUTPUTS[connection.target_service]}",
                    description="Managed resource selected for backup",
                ),
                ModuleInput(
                    module=plan,
                    name=role_variable,
                    value=self._renderer.render_expression(config.role_arn),
                    description="External backup service role",
                ),
            ],
            resources=[
                self._resource(
                    plan,
                    f"selection_{target}.tf",
                    self._renderer.render_resource(
                        "aws_backup_selection",
                        f"selection_{target}",
                        {
                            "name": target,
                            "plan_id": Expr(f"aws_backup_plan.{plan}.id"),
                            "iam_role_arn": Expr(f"var.{role_variable}"),
                            "resources": [Expr(f"var.{variable}")],
                        },
                    ),
                )
            ],
        )
