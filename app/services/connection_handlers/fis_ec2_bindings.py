"""A template owns one explicit instance set independently of connector order."""

import re
from dataclasses import dataclass

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.fis_ec2 import ACTION_NAME_PATTERN, FisEc2Config
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


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
    errors = []
    if any(
        FisEc2Config.model_validate(item.connection_config) != request for item in peers
    ):
        errors.append(
            {
                "loc": ("connection_config",),
                "msg": "All EC2 targets in a template must use the same operation and selection mode",
            }
        )
    if not re.fullmatch(ROLE_ARN_PATTERN, source.config.role_arn):
        errors.append(
            {
                "loc": ("role_arn",),
                "msg": "EC2 experiments require a valid external experiment role ARN",
            }
        )
    if not re.fullmatch(ACTION_NAME_PATTERN, source.config.action_name):
        errors.append(
            {
                "loc": ("action_name",),
                "msg": "Experiment action names require 1–64 letters, numbers, underscores, or hyphens",
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
    for name in targets:
        target = BaseConnectionHandler._find_instance(name, project)
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
                    source.name,
                    source_region,
                    name,
                    target_region,
                    connection.connection_type,
                )
    return FisEc2Binding(targets, request.operation, request.selection_mode)
