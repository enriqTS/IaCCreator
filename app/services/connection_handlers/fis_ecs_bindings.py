"""One connected ECS service supplies each template's dynamic task population."""

from dataclasses import dataclass

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.fis_ecs import FisEcsConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.fis_bindings import (
    experiment_binding_errors,
    validate_experiment_regions,
)


@dataclass(frozen=True)
class FisEcsBinding:
    target: str
    selection_mode: str


def resolve_ecs_fault(connection: ConnectionIR, project: ProjectIR) -> FisEcsBinding:
    peers = [
        item
        for item in project.connections
        if item.source_name == connection.source_name
        and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
        and item.target_service == ServiceType.ECS
        and item.connection_type == "targets"
    ]
    request = FisEcsConfig.model_validate(connection.connection_config)
    targets = tuple(sorted({item.target_name for item in peers}))
    errors = experiment_binding_errors(connection, project)
    if len(targets) != 1:
        errors.append(
            {
                "loc": ("target",),
                "msg": "Each ECS stop-task template must target exactly one connected service",
            }
        )
    if any(
        FisEcsConfig.model_validate(item.connection_config) != request for item in peers
    ):
        errors.append(
            {
                "loc": ("selection_mode",),
                "msg": "Repeated ECS connections must use the same running task selection",
            }
        )
    if errors:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            errors,
        )
    validate_experiment_regions(connection, targets, project)
    return FisEcsBinding(targets[0], request.selection_mode)
