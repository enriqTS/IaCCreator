import hashlib
import re
from dataclasses import dataclass

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.ecr_eks import EcrEksConfig
from app.models.ecr_image import REPOSITORY_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.network_placement import has_placement


@dataclass(frozen=True)
class EksImageBinding:
    repository: str
    settings: EcrEksConfig

    @property
    def key(self) -> str:
        identity = (
            self.settings.namespace,
            self.settings.deployment_name,
            self.settings.container_name,
            self.settings.pull_role_arn,
        )
        return hashlib.sha256("\0".join(identity).encode()).hexdigest()


def resolve_eks_images(name: str, project: ProjectIR) -> list[EksImageBinding]:
    target = BaseConnectionHandler._find_instance(name, project)
    bindings = {}
    images = {}
    role_types = {}
    connections = [
        item
        for item in project.connections
        if item.source_service == ServiceType.ECR
        and item.target_service == ServiceType.EKS
    ]
    for connection in connections:
        request = EcrEksConfig.model_validate(connection.connection_config)
        if (
            request.pull_role_arn in role_types
            and role_types[request.pull_role_arn] != request.pull_role_type
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("pull_role_type",),
                        "msg": "An image pull role must have one compute type across connected clusters",
                    }
                ],
            )
        role_types[request.pull_role_arn] = request.pull_role_type
        if connection.target_name != name:
            continue
        source = BaseConnectionHandler._find_instance(connection.source_name, project)
        errors = []
        if not has_placement(name, "subnet_ids", ServiceType.SUBNET, project):
            errors.append(
                {"loc": ("subnet_ids",), "msg": "EKS requires subnet placement"}
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
        if request.pull_role_arn == target.config.cluster_role_arn:
            errors.append(
                {
                    "loc": ("pull_role_arn",),
                    "msg": "Use the worker or Fargate pod execution role instead of the cluster role",
                }
            )
        workload = (request.namespace, request.deployment_name, request.container_name)
        image = (source.name, request.image_version)
        if workload in images and images[workload] != image:
            errors.append(
                {
                    "loc": ("container_name",),
                    "msg": "Each Deployment container must use one repository and image version",
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
        images[workload] = image
        binding = EksImageBinding(source.name, request)
        bindings[binding.key] = binding
    return [bindings[key] for key in sorted(bindings)]
