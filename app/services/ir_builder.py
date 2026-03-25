"""IR Builder service: transforms validated ArchitectureDescription into ProjectIR."""

from collections import defaultdict

from fastapi import HTTPException

from app.models.input_models import (
    ArchitectureDescription,
    Connection,
    ServiceType,
)
from app.models.ir_models import (
    ConnectionIR,
    EnvironmentIR,
    IAMStatement,
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
}

# IAM action mappings per target service type
IAM_ACTIONS: dict[ServiceType, list[str]] = {
    ServiceType.DYNAMODB: [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
    ],
    ServiceType.S3: [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
    ],
    ServiceType.CLOUDWATCH: [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    ],
}


def _build_iam_resources(target_name: str, target_service: ServiceType) -> list[str]:
    """Build Terraform resource references for IAM statement resources."""
    if target_service == ServiceType.DYNAMODB:
        return [f"${{aws_dynamodb_table.{target_name}.arn}}"]
    elif target_service == ServiceType.S3:
        return [
            f"${{aws_s3_bucket.{target_name}.arn}}",
            f"${{aws_s3_bucket.{target_name}.arn}}/*",
        ]
    elif target_service == ServiceType.CLOUDWATCH:
        return [f"arn:aws:logs:*:*:log-group:/aws/lambda/{target_name}:*"]
    return []


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
            iam_statements = self._derive_iam_statements(instance_connections)

            instance_ir = ResourceInstanceIR(
                name=resource.name,
                service_type=resource.service_type,
                config=resource.config,
                iam_statements=iam_statements,
                connections=instance_connections,
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

        return ProjectIR(
            project_name=input.project_name,
            environments=environments,
            modules=modules,
            connections=connections_ir,
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
                raise HTTPException(
                    status_code=422,
                    detail=f"Connection references non-existent source resource: '{conn.source}'",
                )
            # Validate target exists
            if conn.target not in resource_map:
                raise HTTPException(
                    status_code=422,
                    detail=f"Connection references non-existent target resource: '{conn.target}'",
                )

            source_resource = resource_map[conn.source]
            target_resource = resource_map[conn.target]
            pair = (source_resource.service_type, target_resource.service_type)

            # Validate compatibility
            if pair not in COMPATIBLE_CONNECTIONS:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Incompatible connection: {source_resource.service_type.value} "
                        f"→ {target_resource.service_type.value} is not supported"
                    ),
                )

            result.append(
                ConnectionIR(
                    source_name=conn.source,
                    target_name=conn.target,
                    source_service=source_resource.service_type,
                    target_service=target_resource.service_type,
                    connection_type=conn.connection_type,
                )
            )

        return result

    def _derive_iam_statements(
        self, connections: list[ConnectionIR]
    ) -> list[IAMStatement]:
        """Derive IAM statements for a Lambda based on its outgoing connections."""
        statements: list[IAMStatement] = []

        for conn in connections:
            if conn.source_service != ServiceType.LAMBDA:
                continue

            actions = IAM_ACTIONS.get(conn.target_service)
            if not actions:
                continue

            resources = _build_iam_resources(conn.target_name, conn.target_service)
            if resources:
                statements.append(
                    IAMStatement(
                        effect="Allow",
                        actions=actions,
                        resources=resources,
                    )
                )

        return statements
