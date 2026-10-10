import json
import re
from dataclasses import dataclass

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecs_logs import RESERVED_CONTAINERS
from app.models.connection_configs.ecr_ecs import (
    PRIVATE_ECR_PATTERN,
    REPOSITORY_PATTERN,
    EcrEcsConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecs_collection import ecs_collection_errors


@dataclass(frozen=True)
class EcrImageBinding:
    container: str
    repository: str
    image_version: str


def resolve_registry_images(name: str, project: ProjectIR) -> list[EcrImageBinding]:
    target = BaseConnectionHandler._find_instance(name, project)
    bindings: dict[str, EcrImageBinding] = {}
    connections = [
        item
        for item in project.connections
        if item.target_name == name and item.source_service == ServiceType.ECR
    ]
    for connection in connections:
        source = BaseConnectionHandler._find_instance(connection.source_name, project)
        request = EcrEcsConfig.model_validate(connection.connection_config)
        container = request.container_name or name
        binding = EcrImageBinding(container, source.name, request.image_version)
        errors = ecs_collection_errors(name, project)
        if container in RESERVED_CONTAINERS:
            errors.append(
                {
                    "loc": ("container_name",),
                    "msg": "Managed collectors own their images",
                }
            )
        if container in bindings and bindings[container] != binding:
            errors.append(
                {
                    "loc": ("container_name",),
                    "msg": "Each application container can use only one repository and image version",
                }
            )
        if (
            not re.fullmatch(REPOSITORY_PATTERN, source.config.repository_name or "")
            or not 2 <= len(source.config.repository_name or "") <= 256
        ):
            errors.append(
                {
                    "loc": ("repository_name",),
                    "msg": "Use a valid native private ECR repository name",
                }
            )
        containers = (
            json.loads(target.config.container_definitions)
            if target.config.container_definitions
            else [{"name": name}]
        )
        selected = next(
            (item for item in containers if item["name"] == container), None
        )
        if selected is None:
            errors.append(
                {
                    "loc": ("container_name",),
                    "msg": "Select an existing application container in container_definitions",
                }
            )
        elif selected.get("repositoryCredentials") not in (None, {}):
            errors.append(
                {
                    "loc": ("repositoryCredentials",),
                    "msg": "Remove selected container registry credentials before connecting ECR",
                }
            )
        if errors:
            raise InvalidConnectionConfigError(
                source.name, name, connection.connection_type, errors
            )
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
        bindings[container] = binding
    if target.config.container_definitions and any(
        item["name"] not in bindings and re.match(PRIVATE_ECR_PATTERN, item["image"])
        for item in json.loads(target.config.container_definitions)
    ):
        raise InvalidConnectionConfigError(
            connections[0].source_name,
            name,
            connections[0].connection_type,
            [
                {
                    "loc": ("container_definitions",),
                    "msg": "Connect every application container using a private ECR image so pull permissions remain scoped",
                }
            ],
        )
    return [bindings[container] for container in sorted(bindings)]
