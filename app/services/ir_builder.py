"""IR Builder service: transforms validated ArchitectureDescription into ProjectIR."""

import logging
from collections import defaultdict

from app.exceptions import IncompatibleConnectionError, ResourceNotFoundError

logger = logging.getLogger(__name__)
from app.models.input_models import (
    ArchitectureDescription,
    Connection,
    ServiceType,
)
from app.models.ir_models import (
    ConnectionIR,
    EnvironmentIR,
    GlobalTerraformConfigIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)

# Compatible connection pairs: (source_service, target_service)
COMPATIBLE_CONNECTIONS: set[tuple[ServiceType, ServiceType]] = {
    (ServiceType.API_GATEWAY, ServiceType.LAMBDA),
    (ServiceType.LAMBDA, ServiceType.DYNAMODB),
    (ServiceType.LAMBDA, ServiceType.S3),
    (ServiceType.LAMBDA, ServiceType.CLOUDWATCH),
    (ServiceType.LAMBDA, ServiceType.SNS),
    (ServiceType.LAMBDA, ServiceType.SQS),
    (ServiceType.SQS, ServiceType.LAMBDA),
    (ServiceType.SNS, ServiceType.SQS),
    (ServiceType.SNS, ServiceType.LAMBDA),
}


class IRBuilder:
    """Transforms a validated ArchitectureDescription into a ProjectIR."""

    def build(self, input: ArchitectureDescription) -> ProjectIR:
        """Build the full IR tree from the input description."""
        resource_map = {r.name: r for r in input.resources}

        # Validate connections
        connections_ir = self._build_connections(input.connections, resource_map)

        # Index connections by source for IAM enrichment
        connections_by_source: dict[str, list[ConnectionIR]] = defaultdict(list)
        for conn in connections_ir:
            connections_by_source[conn.source_name].append(conn)

        # Group resources by service type and build ResourceInstanceIR
        service_groups: dict[ServiceType, list[ResourceInstanceIR]] = defaultdict(list)
        for resource in input.resources:
            instance_connections = connections_by_source.get(resource.name, [])

            instance_ir = ResourceInstanceIR(
                name=resource.name,
                service_type=resource.service_type,
                config=resource.config,
                iam_statements=[],
                connections=instance_connections,
                terraform_variables=resource.terraform_variables,
            )
            service_groups[resource.service_type].append(instance_ir)

        # Build service modules
        modules = [
            ServiceModuleIR(service_type=stype, instances=instances)
            for stype, instances in service_groups.items()
        ]

        # Determine which service types are used
        used_service_types = list(service_groups.keys())

        # Build environments
        environments = [
            EnvironmentIR(
                name=env.name,
                variables=env.variables,
                module_refs=used_service_types,
            )
            for env in input.environments
        ]

        # Build global config
        global_config = GlobalTerraformConfigIR(
            backend_type=input.global_terraform_config.backend_type,
            backend_config=input.global_terraform_config.backend_config,
            provider_region=input.global_terraform_config.provider_region,
            provider_profile=input.global_terraform_config.provider_profile,
            terraform_version=input.global_terraform_config.terraform_version,
            aws_provider_version=input.global_terraform_config.aws_provider_version,
        )

        return ProjectIR(
            project_name=input.project_name,
            environments=environments,
            modules=modules,
            connections=connections_ir,
            global_config=global_config,
        )

    def _build_connections(
        self,
        connections: list[Connection],
        resource_map: dict,
    ) -> list[ConnectionIR]:
        """Validate and build ConnectionIR list from input connections."""
        result: list[ConnectionIR] = []

        for conn in connections:
            # Validate source exists
            if conn.source not in resource_map:
                raise ResourceNotFoundError(
                    resource_name=conn.source, direction="source"
                )
            # Validate target exists
            if conn.target not in resource_map:
                raise ResourceNotFoundError(
                    resource_name=conn.target, direction="target"
                )

            source_resource = resource_map[conn.source]
            target_resource = resource_map[conn.target]
            pair = (source_resource.service_type, target_resource.service_type)

            # Validate compatibility
            if pair not in COMPATIBLE_CONNECTIONS:
                raise IncompatibleConnectionError(
                    source_service_type=source_resource.service_type.value,
                    target_service_type=target_resource.service_type.value,
                )

            result.append(
                ConnectionIR(
                    source_name=conn.source,
                    target_name=conn.target,
                    source_service=source_resource.service_type,
                    target_service=target_resource.service_type,
                    connection_type=conn.connection_type,
                    connection_config=conn.connection_config,
                )
            )

        return result
