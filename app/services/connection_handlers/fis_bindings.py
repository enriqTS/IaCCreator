"""Experiment sources share identity, target-family, and effective Region checks."""

import re

from app.exceptions import CrossRegionConnectionError
from app.models.connection_configs.fis import ACTION_NAME_PATTERN
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


def experiment_binding_errors(
    connection: ConnectionIR, project: ProjectIR
) -> list[dict]:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    errors = []
    if not re.fullmatch(ROLE_ARN_PATTERN, source.config.role_arn):
        errors.append(
            {
                "loc": ("role_arn",),
                "msg": "Fault experiments require a valid external experiment role ARN",
            }
        )
    if not re.fullmatch(ACTION_NAME_PATTERN, source.config.action_name):
        errors.append(
            {
                "loc": ("action_name",),
                "msg": "Experiment action names require 1–64 letters, numbers, underscores, or hyphens",
            }
        )
    if any(
        item.source_name == source.name
        and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
        and item.connection_type == "targets"
        and item.target_service != connection.target_service
        for item in project.connections
    ):
        errors.append(
            {
                "loc": ("target",),
                "msg": "Each experiment template supports one target service type; use separate templates for EC2 and ECS faults",
            }
        )
    return errors


def validate_experiment_regions(
    connection: ConnectionIR, targets: tuple[str, ...], project: ProjectIR
) -> None:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
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
