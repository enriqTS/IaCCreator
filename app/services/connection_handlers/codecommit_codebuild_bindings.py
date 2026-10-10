import re

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.codecommit_codebuild import CodeCommitBuildConfig
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


def resolve_repository_source(
    connection: ConnectionIR, project: ProjectIR
) -> CodeCommitBuildConfig:
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    peers = [
        peer
        for peer in project.connections
        if peer.target_name == target.name
        and peer.source_service == ServiceType.CODECOMMIT
    ]
    try:
        if len({peer.source_name for peer in peers}) != 1:
            raise ValueError(
                "One CodeCommit repository must own the build's primary source"
            )
        requests = [
            CodeCommitBuildConfig.model_validate(peer.connection_config)
            for peer in peers
        ]
        if any(request != requests[0] for request in requests):
            raise ValueError(
                "Repeated repository-build connections must agree on revision and clone depth"
            )
        if target.config.source_type not in {None, "NO_SOURCE", "CODECOMMIT"}:
            raise ValueError(
                "A managed CodeCommit source conflicts with the build's configured source type"
            )
        if not re.fullmatch(ROLE_ARN_PATTERN, target.config.service_role or ""):
            raise ValueError(
                "Repository checkout requires a valid external CodeBuild service-role ARN"
            )
    except ValueError as exc:
        raise InvalidConnectionConfigError(
            connection.source_name,
            target.name,
            connection.connection_type,
            [{"loc": ("repository_source",), "msg": str(exc)}],
        ) from exc
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
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
