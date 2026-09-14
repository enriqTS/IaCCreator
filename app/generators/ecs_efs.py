"""Compose EFS volumes with existing container transformations."""

from app.generators.hcl_renderer import Expr


def add_efs_task_attributes(attrs: dict) -> None:
    containers = attrs["container_definitions"]
    attrs['dynamic "volume"'] = {
        "for_each": Expr("local.efs_mounts"),
        "content": {
            "name": Expr("volume.value.name"),
            "efs_volume_configuration": {
                "file_system_id": Expr("volume.value.filesystem_id"),
                "root_directory": "/",
                "transit_encryption": "ENABLED",
                "authorization_config": {
                    "access_point_id": Expr("volume.value.access_point_id"),
                    "iam": "ENABLED",
                },
            },
        },
    }
    paths = "[for mount in local.efs_mounts : mount.path if mount.container == container.name]"
    attrs["container_definitions"] = Expr(
        f"jsonencode([for container in jsondecode({containers}) : merge(container, {{mountPoints = concat([for mount in try(container.mountPoints, []) : mount if !contains({paths}, mount.containerPath)], [for mount in local.efs_mounts : {{sourceVolume = mount.name, containerPath = mount.path, readOnly = mount.read_only}} if mount.container == container.name])}})])"
    )
    precondition = {
        "condition": Expr(
            "alltrue([for mount in local.efs_mounts : contains([for container in jsondecode(var.container_definitions) : container.name], mount.container)])"
        ),
        "error_message": "Every EFS mount must name a container in container_definitions.",
    }
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + [precondition]
