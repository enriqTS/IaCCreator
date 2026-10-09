"""A template owns one explicit instance set independently of connector order."""

from dataclasses import dataclass

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.fis_ec2 import FisEc2Config
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.fis_bindings import (
    experiment_binding_errors,
    validate_experiment_regions,
)


@dataclass(frozen=True)
class FisEc2Binding:
    targets: tuple[str, ...]
    operation: str
    selection_mode: str


def resolve_ec2_fault(connection: ConnectionIR, project: ProjectIR) -> FisEc2Binding:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    peers = [
        item
        for item in project.connections
        if item.source_name == source.name
        and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
        and item.target_service == ServiceType.EC2
        and item.connection_type == "targets"
    ]
    request = FisEc2Config.model_validate(connection.connection_config)
    targets = tuple(sorted({item.target_name for item in peers}))
    errors = experiment_binding_errors(connection, project)
    if any(
        FisEc2Config.model_validate(item.connection_config) != request for item in peers
    ):
        errors.append(
            {
                "loc": ("connection_config",),
                "msg": "All EC2 targets in a template must use the same operation and selection mode",
            }
        )
    if not 1 <= len(targets) <= 5:
        errors.append(
            {
                "loc": ("target",),
                "msg": "An explicit EC2 experiment target supports one to five distinct instances",
            }
        )
    if request.selection_mode != "ALL" and int(request.selection_mode[6:-1]) > len(
        targets
    ):
        errors.append(
            {
                "loc": ("selection_mode",),
                "msg": "The selection count cannot exceed the connected instance count",
            }
        )
    if errors:
        raise InvalidConnectionConfigError(
            source.name, connection.target_name, connection.connection_type, errors
        )
    validate_experiment_regions(connection, targets, project)
    return FisEc2Binding(targets, request.operation, request.selection_mode)
