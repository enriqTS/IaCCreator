"""Shared access-point ownership and deterministic runtime mount bindings."""

import hashlib
from dataclasses import dataclass

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.efs import EfsClientMountConfig
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


@dataclass
class EfsMount:
    name: str
    filesystem: str
    container: str
    config: EfsClientMountConfig

    def entry(self) -> dict:
        return {
            "name": self.name,
            "container": self.container,
            "path": self.config.local_mount_path,
            "read_only": self.config.access == "read",
            "filesystem_id": Expr(f"var.{self.name}_filesystem_id"),
            "filesystem_arn": Expr(f"var.{self.name}_filesystem_arn"),
            "access_point_id": Expr(f"var.{self.name}_access_point_id"),
        }


def reject_mount(connection: ConnectionIR, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": ("mount",), "msg": message}],
    )


def has_placement(
    name: str, field: str, service: ServiceType, project: ProjectIR
) -> bool:
    instance = BaseConnectionHandler._find_instance(name, project)
    return bool(getattr(instance.config, field, None)) or any(
        item.source_service == service
        and item.target_name == name
        and item.connection_type in {"places", "associates"}
        for item in project.connections
    )


class EfsClientMounts(BaseConnectionHandler):
    def build(
        self,
        connection: ConnectionIR,
        project: ProjectIR,
        model: type[EfsClientMountConfig],
    ) -> tuple[list[EfsMount], ConnectionContribution]:
        consumer = connection.target_name
        bindings = {}
        for item in project.connections:
            if (
                item.target_name != consumer
                or item.source_service != ServiceType.EFS
                or item.connection_type != "mounts"
            ):
                continue
            config = model.model_validate(item.connection_config)
            container = getattr(config, "container_name", None) or consumer
            key = (container, config.local_mount_path)
            value = (item.source_name, config)
            if key in bindings and bindings[key] != value:
                reject_mount(
                    connection, "Conflicting EFS mounts at the same runtime path"
                )
            bindings[key] = value
        paths = sorted(bindings)
        if any(
            a[0] == b[0] and b[1].startswith(a[1] + "/")
            for a in paths
            for b in paths
            if a != b
        ):
            reject_mount(connection, "Managed EFS mount paths cannot overlap")
        result = ConnectionContribution()
        mounts = []
        for (container, path), (filesystem, config) in sorted(bindings.items()):
            if not has_placement(filesystem, "subnet_ids", ServiceType.SUBNET, project):
                reject_mount(
                    connection, "EFS requires subnet placement for mount targets"
                )
            name = (
                "efs_"
                + hashlib.sha256(
                    repr(
                        (
                            consumer,
                            filesystem,
                            container,
                            getattr(config, "storage_identity", path),
                        )
                    ).encode()
                ).hexdigest()[:16]
            )
            mounts.append(EfsMount(name, filesystem, container, config))
            resource = self._renderer.render_resource(
                "aws_efs_access_point",
                name,
                {
                    "file_system_id": Expr(f"aws_efs_file_system.{filesystem}.id"),
                    "posix_user": {"uid": config.uid, "gid": config.gid},
                    "root_directory": {
                        "path": config.root_directory or f"/{name}",
                        "creation_info": {
                            "owner_uid": config.uid,
                            "owner_gid": config.gid,
                            "permissions": "0770",
                        },
                    },
                },
            )
            result.resources.append(self._resource(filesystem, f"{name}.tf", resource))
            for suffix, expression in [
                ("filesystem_id", f"aws_efs_file_system.{filesystem}.id"),
                ("filesystem_arn", f"aws_efs_file_system.{filesystem}.arn"),
                ("access_point_id", f"aws_efs_access_point.{name}.id"),
            ]:
                result.outputs.append(
                    ModuleOutput(
                        module=filesystem,
                        name=f"{name}_{suffix}",
                        value=expression,
                        description="Mount-ready EFS reference",
                        depends_on=[f"aws_efs_mount_target.{filesystem}"],
                    )
                )
                result.inputs.append(
                    ModuleInput(
                        module=consumer,
                        name=f"{name}_{suffix}",
                        value=f"module.{filesystem}.{name}_{suffix}",
                        description="Managed EFS mount reference",
                    )
                )
        return mounts, result
