"""Linux EC2 mounts share runtime credentials with existing secret connections."""

from pathlib import Path

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.efs import EfsEc2MountConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ec2_runtime_role import Ec2RuntimeRole
from app.services.connection_handlers.efs_client_mounts import (
    EfsClientMounts,
    has_placement,
    reject_mount,
)


class EfsEc2MountHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Requires a Linux cloud-init AMI with amazon-efs-utils, or explicit Amazon Linux helper installation. Mount changes replace the instance to rerun bootstrap. EFS targets need TCP 2049 reachability; shell user data runs after mounts succeed.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        consumer = self._find_instance(connection.target_name, project)
        for field, service in [
            ("subnet_id", ServiceType.SUBNET),
            ("security_group_ids", ServiceType.SECURITY_GROUP),
        ]:
            if not has_placement(consumer.name, field, service, project):
                reject_mount(
                    connection,
                    "EC2 EFS mounts require subnet and security-group placement",
                )
        script = consumer.config.user_data.lstrip()
        if script and not script.startswith(
            (
                "#!/bin/bash\n",
                "#!/bin/sh\n",
                "#!/usr/bin/env bash\n",
                "#!/usr/bin/env sh\n",
            )
        ):
            reject_mount(
                connection,
                "Managed EFS bootstrap requires shell user data with a bash or sh shebang",
            )
        mounts, result = EfsClientMounts().build(connection, project, EfsEc2MountConfig)
        installs = {mount.config.install_efs_utils for mount in mounts}
        if len(installs) > 1:
            reject_mount(
                connection,
                "All mounts on an EC2 instance must agree on EFS helper installation",
            )
        consumer.config._mounts_efs = True
        result.merge(Ec2RuntimeRole().build(consumer.name))
        entries = [mount.entry() for mount in mounts]
        content = (
            "locals {\n  efs_mounts = "
            + self._renderer.render_expression(entries)
            + "\n  install_efs_utils = "
            + self._renderer.render_expression(next(iter(installs)))
            + "\n}\n"
        )
        result.resources.append(self._resource(consumer.name, "efs_mounts.tf", content))
        template = (
            Path(__file__).parents[2] / "generators/templates/efs_bootstrap.sh.tftpl"
        )
        result.resources.append(
            self._resource(
                consumer.name, "efs_bootstrap.sh.tftpl", template.read_text()
            )
        )
        statements = []
        for mount in mounts:
            actions = ["elasticfilesystem:ClientMount"]
            if mount.config.access == "write":
                actions.append("elasticfilesystem:ClientWrite")
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": Expr(f"var.{mount.name}_filesystem_arn"),
                }
            )
        result.resources.append(
            self._resource(
                consumer.name,
                "efs_policy.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "efs_mounts",
                    {
                        "name_prefix": "efs-mounts-",
                        "role": Expr(f"aws_iam_role.{consumer.name}_role.id"),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
        return result
