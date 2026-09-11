"""EFS owns access points; Lambda consumes a mount-ready ARN and client grants."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.storage import EfsLambdaMountConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class EfsLambdaMountHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Lambda and EFS mount targets must share a VPC, with one mount target per Lambda Availability Zone and security groups allowing NFS TCP 2049. Network rules are configured separately.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        filesystem, function = connection.source_name, connection.target_name
        config = EfsLambdaMountConfig.model_validate(connection.connection_config)
        bindings = {
            (
                item.source_name,
                EfsLambdaMountConfig.model_validate(
                    item.connection_config
                ).model_dump_json(),
            )
            for item in project.connections
            if item.target_name == function
            and item.source_service == ServiceType.EFS
            and item.connection_type == "mounts"
        }
        if len(bindings) != 1:
            self._reject(connection, "Lambda supports one EFS filesystem configuration")
        for name, field, service, kind in (
            (filesystem, "subnet_ids", ServiceType.SUBNET, "places"),
            (function, "vpc_subnet_ids", ServiceType.SUBNET, "places"),
            (
                function,
                "vpc_security_group_ids",
                ServiceType.SECURITY_GROUP,
                "associates",
            ),
        ):
            instance = self._find_instance(name, project)
            if not getattr(instance.config, field, None) and not any(
                item.target_name == name
                and item.source_service == service
                and item.connection_type == kind
                for item in project.connections
            ):
                self._reject(
                    connection,
                    f"{name} requires {field} or managed placement connections",
                )
        target = self._find_instance(function, project)
        target.config.file_system_arn = "managed-by-connection"
        target.config.file_system_local_mount_path = config.local_mount_path
        point = f"{safe_identifier(function)}_access_point"
        resource = self._renderer.render_resource(
            "aws_efs_access_point",
            point,
            {
                "file_system_id": Expr(f"aws_efs_file_system.{filesystem}.id"),
                "posix_user": {"uid": config.uid, "gid": config.gid},
                "root_directory": {
                    "path": config.root_directory or f"/{function}",
                    "creation_info": {
                        "owner_uid": config.uid,
                        "owner_gid": config.gid,
                        "permissions": "0770",
                    },
                },
            },
        )
        actions = ["elasticfilesystem:ClientMount"]
        if config.access == "write":
            actions.append("elasticfilesystem:ClientWrite")
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=function,
                    name="file_system_arn",
                    value=f"module.{filesystem}.{point}_arn",
                    description="Mount-ready EFS access point",
                ),
                ModuleInput(
                    module=function,
                    name="file_system_local_mount_path",
                    value=self._renderer.render_expression(config.local_mount_path),
                    description="Lambda filesystem mount path",
                ),
            ],
            outputs=[
                ModuleOutput(
                    module=filesystem,
                    name=f"{point}_arn",
                    value=f"aws_efs_access_point.{point}.arn",
                    description="EFS access point available after mount targets",
                    depends_on=[f"aws_efs_mount_target.{filesystem}"],
                )
            ],
            resources=[self._resource(filesystem, f"{point}.tf", resource)],
            iam=[
                self._grant(
                    function,
                    IAMStatement(
                        actions=actions,
                        resources=[f"${{aws_efs_file_system.{filesystem}.arn}}"],
                    ),
                ),
                self._grant(
                    function,
                    IAMStatement(
                        actions=[
                            "ec2:CreateNetworkInterface",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DescribeSubnets",
                            "ec2:DeleteNetworkInterface",
                            "ec2:AssignPrivateIpAddresses",
                            "ec2:UnassignPrivateIpAddresses",
                        ],
                        resources=["*"],
                    ),
                ),
            ],
        )

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("file_system_arn",), "msg": message}],
        )
