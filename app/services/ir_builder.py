"""IR Builder service: transforms validated ArchitectureDescription into ProjectIR."""

import logging
from collections import defaultdict

from pydantic import ValidationError

from app.exceptions import (
    CrossRegionConnectionError,
    IncompatibleConnectionError,
    InvalidConnectionConfigError,
    ResourceNotFoundError,
)
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import (
    _get_cached_service_config_models,
)
from app.models.input_models.api_gateway_route import route_dicts

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
        # Ids survive renames, so they take precedence when the client supplies them
        id_map = {r.id: r for r in input.resources if r.id}

        # Validate connections
        connections_ir = self._build_connections(
            input.connections, resource_map, id_map
        )

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
                provider_region=resource.provider_region,
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

    @staticmethod
    def _resolve_endpoint(
        name: str,
        endpoint_id: str | None,
        direction: str,
        resource_map: dict,
        id_map: dict,
    ):
        """Find a connection endpoint by stable id when given one, otherwise by name."""
        if endpoint_id and endpoint_id in id_map:
            return id_map[endpoint_id]
        if name in resource_map:
            return resource_map[name]
        raise ResourceNotFoundError(resource_name=name, direction=direction)

    def _build_connections(
        self,
        connections: list[Connection],
        resource_map: dict,
        id_map: dict | None = None,
    ) -> list[ConnectionIR]:
        """Validate and build ConnectionIR list from input connections."""
        result: list[ConnectionIR] = []
        id_map = id_map or {}

        for conn in connections:
            source_resource = self._resolve_endpoint(
                conn.source, conn.source_id, "source", resource_map, id_map
            )
            target_resource = self._resolve_endpoint(
                conn.target, conn.target_id, "target", resource_map, id_map
            )
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

            self._validate_connection_regions(source_resource, target_resource, spec)
            connection_config = conn.connection_config

            # Derive routes from API Gateway config for route_handler connections
            if spec.connection_type == "route_handler":
                connection_config = self._derive_apigw_lambda_routes(
                    conn, source_resource, target_resource
                )

            validated_config = self._validate_config(conn, spec, connection_config)

            # A consumed stream has to exist, so the connection turns it on
            if spec.connection_type == "streams_to":
                self._enable_source_stream(source_resource, validated_config)

            result.append(
                ConnectionIR(
                    source_name=source_resource.name,
                    target_name=target_resource.name,
                    source_id=source_resource.id,
                    target_id=target_resource.id,
                    source_service=source_resource.service_type,
                    target_service=target_resource.service_type,
                    connection_type=spec.connection_type,
                    connection_config=validated_config,
                )
            )

        return result

    @staticmethod
    def _validate_connection_regions(source_resource, target_resource, spec) -> None:
        source_region = source_resource.provider_region
        target_region = target_resource.provider_region
        if (
            spec.region_policy == "same-region"
            and source_region
            and target_region
            and source_region != target_region
        ):
            raise CrossRegionConnectionError(
                source_resource.name,
                source_region,
                target_resource.name,
                target_region,
                spec.connection_type,
            )

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

    @staticmethod
    def _enable_source_stream(source_resource, connection_config: dict) -> None:
        """Turn on the source table's stream so the consuming function has one to read."""
        config = source_resource.config
        if not hasattr(config, "stream_enabled"):
            return
        config.stream_enabled = True
        # The table's own choice wins; the connection only supplies a default
        if getattr(config, "stream_view_type", None) is None:
            config.stream_view_type = connection_config.get(
                "stream_view_type", "NEW_AND_OLD_IMAGES"
            )

    def _derive_apigw_lambda_routes(
        self,
        conn: Connection,
        source_resource,
        target_resource,
    ) -> dict:
        """Derive routes array from API Gateway config for route_handler connections.

        For API_GATEWAY -> LAMBDA connections with role 'route_handler' (default),
        derives connection_config['routes'] from the gateway's config.routes
        entries whose integration_id (or integration_name) matches the target lambda.

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
        routes = route_dicts(getattr(source_config, "routes", None))
        if not routes:
            return config

        target_name = target_resource.name
        target_id = getattr(target_resource, "id", None)
        derived_routes: list[dict] = []

        for route in routes:
            # Match on the stable id when the route carries one, so renames cannot orphan it
            route_id = route.get("integration_id")
            if route_id:
                if route_id != target_id:
                    continue
            elif route.get("integration_name") != target_name:
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
