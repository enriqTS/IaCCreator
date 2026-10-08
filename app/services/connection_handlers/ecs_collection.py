"""Managed collectors require the same modeled task launch and placement."""

from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.network_placement import has_placement


def ecs_collection_errors(name: str, project: ProjectIR) -> list[dict]:
    source = BaseConnectionHandler._find_instance(name, project)
    errors = []
    for field, service in (
        ("subnet_ids", ServiceType.SUBNET),
        ("security_group_ids", ServiceType.SECURITY_GROUP),
    ):
        if not has_placement(name, field, service, project):
            errors.append(
                {
                    "loc": (field,),
                    "msg": "ECS collection requires subnet and security-group placement",
                }
            )
    if source.config.ecs_launch_type not in {None, "FARGATE"}:
        errors.append(
            {
                "loc": ("ecs_launch_type",),
                "msg": "ECS collection supports the modeled Linux Fargate task",
            }
        )
    return errors
