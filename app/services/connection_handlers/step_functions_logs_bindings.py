"""Each workflow has one deterministic execution-log destination and settings."""

import re

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.step_functions_logs import (
    ROLE_ARN_PATTERN,
    StepFunctionsLogsConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


def resolve_workflow_logs(
    connection: ConnectionIR, project: ProjectIR
) -> StepFunctionsLogsConfig:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    request = StepFunctionsLogsConfig.model_validate(connection.connection_config)
    peers = [
        item
        for item in project.connections
        if item.source_name == source.name
        and item.source_service == ServiceType.STEP_FUNCTIONS
        and item.target_service == ServiceType.CLOUDWATCH
        and item.connection_type == "logs_to"
    ]
    errors = []
    if len({item.target_name for item in peers}) > 1:
        errors.append(
            {
                "loc": ("target",),
                "msg": "A workflow can use only one execution-log destination",
            }
        )
    if any(
        StepFunctionsLogsConfig.model_validate(item.connection_config) != request
        for item in peers
    ):
        errors.append(
            {
                "loc": ("connection_config",),
                "msg": "Repeated workflow logging connections must use identical settings",
            }
        )
    if not re.fullmatch(ROLE_ARN_PATTERN, source.config.role_arn):
        errors.append(
            {
                "loc": ("role_arn",),
                "msg": "Execution logging requires a valid external execution role ARN",
            }
        )
    if source.config.state_machine_type not in {"STANDARD", "EXPRESS"}:
        errors.append(
            {
                "loc": ("state_machine_type",),
                "msg": "Execution logging supports Standard and Express workflows",
            }
        )
    if target.config.log_group_class not in {None, "STANDARD", "INFREQUENT_ACCESS"}:
        errors.append(
            {
                "loc": ("log_group_class",),
                "msg": "Execution logging requires a Standard or Infrequent Access log group",
            }
        )
    if errors:
        raise InvalidConnectionConfigError(
            source.name, target.name, connection.connection_type, errors
        )
    for environment in project.environments:
        override = environment.variables.get("region")
        source_region = (
            override or source.provider_region or project.global_config.provider_region
        )
        target_region = (
            override or target.provider_region or project.global_config.provider_region
        )
        if source_region != target_region:
            raise CrossRegionConnectionError(
                source.name,
                source_region,
                target.name,
                target_region,
                connection.connection_type,
            )
    return request
