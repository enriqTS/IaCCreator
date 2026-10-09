"""Application log destinations have one deterministic owner per container."""

from dataclasses import dataclass

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecs_logs import RESERVED_CONTAINERS
from app.models.connection_configs.ecs_logs import EcsLogsConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecs_collection import ecs_collection_errors


@dataclass(frozen=True)
class EcsLogBinding:
    container_name: str
    log_group: str
    stream_prefix: str
    mode: str
    buffer_size_mib: int


def resolve_ecs_logs(name: str, project: ProjectIR) -> list[EcsLogBinding]:
    source = BaseConnectionHandler._find_instance(name, project)
    bindings: dict[str, EcsLogBinding] = {}
    for connection in project.connections:
        if not (
            connection.source_name == name
            and connection.source_service == ServiceType.ECS
            and connection.target_service == ServiceType.CLOUDWATCH
            and connection.connection_type == "logs_to"
        ):
            continue
        request = EcsLogsConfig.model_validate(connection.connection_config)
        container = request.container_name or name
        errors = ecs_collection_errors(name, project)
        if container in RESERVED_CONTAINERS:
            errors.append(
                {
                    "loc": ("container_name",),
                    "msg": "Managed collectors keep their own diagnostic log destinations",
                }
            )
        binding = EcsLogBinding(
            container,
            connection.target_name,
            request.stream_prefix,
            request.mode,
            request.buffer_size_mib if request.mode == "non-blocking" else 0,
        )
        if container in bindings and bindings[container] != binding:
            errors.append(
                {
                    "loc": ("container_name",),
                    "msg": "Each application container can use only one managed log destination and delivery configuration",
                }
            )
        if errors:
            raise InvalidConnectionConfigError(
                name, connection.target_name, connection.connection_type, errors
            )
        target = BaseConnectionHandler._find_instance(connection.target_name, project)
        for environment in project.environments:
            override = environment.variables.get("region")
            source_region = (
                override
                or source.provider_region
                or project.global_config.provider_region
            )
            target_region = (
                override
                or target.provider_region
                or project.global_config.provider_region
            )
            if source_region != target_region:
                raise CrossRegionConnectionError(
                    name,
                    source_region,
                    target.name,
                    target_region,
                    connection.connection_type,
                )
        bindings[container] = binding
    return [bindings[container] for container in sorted(bindings)]
