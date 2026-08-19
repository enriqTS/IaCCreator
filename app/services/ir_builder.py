"""IR Builder service: transforms validated ArchitectureDescription into ProjectIR."""

import logging
from collections import defaultdict

from pydantic import ValidationError

from app.exceptions import (
    IncompatibleConnectionError,
    InvalidConnectionConfigError,
    ResourceNotFoundError,
)
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import (
    _get_cached_service_config_models,
)

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
from app.services.connection_handlers.registry import (
    COMPATIBLE_CONNECTIONS,
    resolve_spec,
)


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
            resolved_config = self._resolve_config(
                resource.config, resource.service_type
            )

            instance_ir = ResourceInstanceIR(
                name=resource.name,
                service_type=resource.service_type,
                config=resolved_config,
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

            spec = resolve_spec(
                pair[0], pair[1], conn.connection_type, conn.connection_config
            )
            if spec is None:
                raise IncompatibleConnectionError(
                    source_service_type=source_resource.service_type.value,
                    target_service_type=target_resource.service_type.value,
                )

            connection_config = conn.connection_config

            # Derive routes from API Gateway config for route_handler connections
            if spec.connection_type == "route_handler":
                connection_config = self._derive_apigw_lambda_routes(
                    conn, source_resource, target_resource
                )

            result.append(
                ConnectionIR(
                    source_name=conn.source,
                    target_name=conn.target,
                    source_service=source_resource.service_type,
                    target_service=target_resource.service_type,
                    connection_type=spec.connection_type,
                    connection_config=self._validate_config(
                        conn, spec, connection_config
                    ),
                )
            )

        return result

    @staticmethod
    def _validate_config(conn: Connection, spec, connection_config: dict) -> dict:
        """Validate a connection's config against its spec, then normalise it."""
        payload = dict(connection_config)
        # connection_role selected the spec; it is not part of the config itself
        payload.pop("connection_role", None)
        try:
            validated = spec.config_model.model_validate(payload)
        except ValidationError as exc:
            raise InvalidConnectionConfigError(
                source=conn.source,
                target=conn.target,
                connection_type=spec.connection_type,
                errors=exc.errors(),
            ) from exc
        return validated.model_dump(exclude_none=True)

    def _derive_apigw_lambda_routes(
        self,
        conn: Connection,
        source_resource,
        target_resource,
    ) -> dict:
        """Derive routes array from API Gateway config for route_handler connections.

        For API_GATEWAY -> LAMBDA connections with role 'route_handler' (default),
        derives connection_config['routes'] from the gateway's config.routes
        entries where integration_name matches the target lambda name.

        Preserves explicit connection_config['routes'] if already present
        (direct API/back-compat use).
        """
        config = conn.connection_config or {}

        # Skip if routes already explicitly provided (direct API/back-compat)
        if config.get("routes"):
            return config

        # Only process route_handler role (default when not specified)
        role = config.get("connection_role", "route_handler")
        if role != "route_handler":
            return config

        # Get source gateway's routes configuration
        source_config = source_resource.config
        if not source_config:
            return config

        # Skip WebSocket APIs (handled separately)
        protocol_type = getattr(source_config, "protocol_type", None)
        if protocol_type == "WEBSOCKET":
            return config

        # Get the routes array from gateway config
        routes = getattr(source_config, "routes", None)
        if not routes:
            return config

        target_name = target_resource.name
        derived_routes: list[dict] = []

        for route in routes:
            # Check if this route targets the lambda
            if route.get("integration_name") != target_name:
                continue

            # Build route entry for connection_config
            methods = route.get("methods", ["ANY"])
            path = route.get("path", "/")

            route_entry: dict = {
                "methods": methods if isinstance(methods, list) else [str(methods)],
                "path": path,
            }

            # Optional fields
            if route.get("route_response_key"):
                route_entry["route_response_key"] = route["route_response_key"]
            if route.get("api_key_required"):
                route_entry["api_key_required"] = True

            derived_routes.append(route_entry)

        if derived_routes:
            config = dict(config)  # Shallow copy to avoid mutating original
            config["routes"] = derived_routes

        return config

    def _resolve_config(
        self,
        config: BaseServiceConfig,
        service_type: ServiceType,
    ) -> BaseServiceConfig:
        """Resolve the config to a typed BaseServiceConfig subclass if possible.

        If the config is already a BaseServiceConfig subclass with a Terraform schema,
        it is used directly. Otherwise, BaseServiceConfig is returned as-is for
        icon-only services without a registered model.

        Args:
            config: The resource config from input (BaseServiceConfig or subclass).
            service_type: The service type for registry lookup.

        Returns:
            The resolved config — a typed BaseServiceConfig subclass or base instance.
        """
        # If config is already a typed BaseServiceConfig subclass, use it directly
        if config.has_terraform_schema():
            return config

        # Check if this service has a registered typed config model
        registry = _get_cached_service_config_models()
        config_cls = registry.get(service_type)

        if config_cls is not None and config_cls.has_terraform_schema():
            # Service is migrated — input layer now supplies typed configs directly.
            pass

        return config
