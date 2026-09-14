"""ECS task volumes consume access points with scoped client permissions."""

from app.models.connection_configs.efs import EfsEcsMountConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.efs_client_mounts import (
    EfsClientMounts,
    has_placement,
    reject_mount,
)


class EfsEcsMountHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="ECS and EFS need network reachability on TCP 2049 and mount targets in workload Availability Zones. Linux Fargate requires platform 1.4.0 or later; EC2 capacity requires an EFS-capable ECS agent. Network rules and capacity are configured separately.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        consumer = self._find_instance(connection.target_name, project)
        for field, service in [
            ("subnet_ids", ServiceType.SUBNET),
            ("security_group_ids", ServiceType.SECURITY_GROUP),
        ]:
            if not has_placement(consumer.name, field, service, project):
                reject_mount(
                    connection,
                    "ECS EFS mounts require subnet and security-group placement",
                )
        mounts, result = EfsClientMounts().build(connection, project, EfsEcsMountConfig)
        consumer.config._mounts_efs = True
        content = (
            "locals {\n  efs_mounts = "
            + self._renderer.render_expression([mount.entry() for mount in mounts])
            + "\n}\n"
        )
        result.resources.append(self._resource(consumer.name, "efs_mounts.tf", content))
        for mount in mounts:
            actions = ["elasticfilesystem:ClientMount"]
            if mount.config.access == "write":
                actions.append("elasticfilesystem:ClientWrite")
            result.iam.append(
                self._grant(
                    consumer.name,
                    IAMStatement(
                        actions=actions,
                        resources=[f"${{aws_efs_file_system.{mount.filesystem}.arn}}"],
                    ),
                )
            )
        return result
