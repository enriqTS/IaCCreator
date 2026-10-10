import re

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.codeartifact_codebuild import (
    DOMAIN_PATTERN,
    REPOSITORY_PATTERN,
    CodeArtifactBuildConfig,
)
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.codeartifact_buildspec import (
    validate_package_buildspec,
)


def resolve_package_source(
    connection: ConnectionIR, project: ProjectIR
) -> CodeArtifactBuildConfig:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    peers = [
        peer
        for peer in project.connections
        if peer.target_name == target.name
        and peer.source_service == ServiceType.CODEARTIFACT
    ]
    try:
        if len({peer.source_name for peer in peers}) != 1:
            raise ValueError(
                "One CodeArtifact repository must own the build's package login"
            )
        requests = [
            CodeArtifactBuildConfig.model_validate(peer.connection_config)
            for peer in peers
        ]
        if any(request != requests[0] for request in requests):
            raise ValueError(
                "Repeated package-source connections must agree on the package manager"
            )
        if not re.fullmatch(ROLE_ARN_PATTERN, target.config.service_role or ""):
            raise ValueError(
                "Package login requires a valid external CodeBuild service-role ARN"
            )
        if not re.fullmatch(
            DOMAIN_PATTERN, source.config.domain_name
        ) or not re.fullmatch(REPOSITORY_PATTERN, source.config.repository_name):
            raise ValueError(
                "Package login requires valid CodeArtifact domain and repository names"
            )
        validate_package_buildspec(target.config.buildspec)
    except ValueError as exc:
        raise InvalidConnectionConfigError(
            connection.source_name,
            target.name,
            connection.connection_type,
            [{"loc": ("package_source",), "msg": str(exc)}],
        ) from exc
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
    return requests[0]
