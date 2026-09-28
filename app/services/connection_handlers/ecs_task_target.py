"""Validate and prepare a managed ECS Fargate task for event sources."""

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR, ResourceInstanceIR


def prepare_fargate_target(
    connection: ConnectionIR, project: ProjectIR, target: ResourceInstanceIR
) -> None:
    config = target.config
    managed_subnets = any(
        peer.source_service == ServiceType.SUBNET
        and peer.target_name == connection.target_name
        and peer.connection_type == "places"
        for peer in project.connections
    )
    external_subnets = any(
        value != "managed-by-connection" for value in config.subnet_ids
    )
    if config.ecs_launch_type not in (None, "FARGATE") or not (
        external_subnets or managed_subnets
    ):
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [
                {
                    "loc": ("subnet_ids",),
                    "msg": "ECS task targets require Fargate and at least one task subnet",
                }
            ],
        )
    if managed_subnets and not config.subnet_ids:
        config.subnet_ids = ["managed-by-connection"]
    config._requires_task_role = True
