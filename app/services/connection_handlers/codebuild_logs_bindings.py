"""Build projects have one log group and one deterministic stream prefix."""

import re

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.codebuild_logs import (
    KMS_KEY_ARN_PATTERN,
    CodeBuildLogsConfig,
)
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


def resolve_build_logs(
    connection: ConnectionIR, project: ProjectIR
) -> CodeBuildLogsConfig:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    request = CodeBuildLogsConfig.model_validate(connection.connection_config)
    peers = [
        item
        for item in project.connections
        if item.source_name == source.name
        and item.source_service == ServiceType.CODEBUILD
        and item.target_service == ServiceType.CLOUDWATCH
        and item.connection_type == "logs_to"
    ]
    errors = []
    if len({item.target_name for item in peers}) > 1:
        errors.append(
            {
                "loc": ("target",),
                "msg": "A build project can use only one managed log group",
            }
        )
    if any(
        CodeBuildLogsConfig.model_validate(item.connection_config) != request
        for item in peers
    ):
        errors.append(
            {
                "loc": ("stream_prefix",),
                "msg": "Repeated build logging connections must use identical stream prefixes",
            }
        )
    if not re.fullmatch(ROLE_ARN_PATTERN, source.config.service_role or ""):
        errors.append(
            {
                "loc": ("service_role",),
                "msg": "Build logging requires a valid external service role ARN",
            }
        )
    if target.config.log_group_class not in {None, "STANDARD", "INFREQUENT_ACCESS"}:
        errors.append(
            {
                "loc": ("log_group_class",),
                "msg": "Build logging requires a Standard or Infrequent Access log group",
            }
        )
    external_key = target.config.kms_key_id
    if (
        external_key
        and not managed_key(target.name, project)
        and not re.fullmatch(KMS_KEY_ARN_PATTERN, external_key)
    ):
        errors.append(
            {
                "loc": ("kms_key_id",),
                "msg": "Encrypted build logs require an external KMS key ARN, not an alias or key ID",
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
