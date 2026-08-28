"""Domain-specific exceptions, independent of any HTTP framework."""


class DomainError(Exception):
    """Base class for all domain exceptions."""

    pass


class ResourceNotFoundError(DomainError):
    """Raised when a connection references a non-existent resource."""

    def __init__(self, resource_name: str, direction: str):
        self.resource_name = resource_name
        self.direction = direction
        super().__init__(
            f"Connection references non-existent {direction} resource: '{resource_name}'"
        )


class IncompatibleConnectionError(DomainError):
    """Raised when a connection references an unsupported service-type pair."""

    def __init__(self, source_service_type: str, target_service_type: str):
        self.source_service_type = source_service_type
        self.target_service_type = target_service_type
        super().__init__(
            f"Incompatible connection: {source_service_type} → {target_service_type} is not supported"
        )


class CrossRegionConnectionError(DomainError):
    """Raised when a connection requires both endpoints in one AWS Region."""

    def __init__(
        self,
        source: str,
        source_region: str,
        target: str,
        target_region: str,
        connection_type: str,
    ):
        self.source = source
        self.source_region = source_region
        self.target = target
        self.target_region = target_region
        self.connection_type = connection_type
        super().__init__(
            f"Connection '{source}' ({source_region}) → '{target}' ({target_region}) "
            f"cannot use '{connection_type}' across Regions"
        )


class GeneratorConfigError(DomainError):
    """Raised when a generator receives a config instance of an unexpected type."""

    pass


class InvalidConnectionConfigError(DomainError):
    """Raised when a connection's configuration fails validation against its schema."""

    def __init__(
        self, source: str, target: str, connection_type: str, errors: list[dict]
    ):
        self.source = source
        self.target = target
        self.connection_type = connection_type
        self.errors = errors
        fields = ", ".join(
            f"{'.'.join(str(p) for p in e.get('loc', ())) or 'config'}: {e.get('msg', '')}"
            for e in errors
        )
        super().__init__(
            f"Invalid configuration for connection '{source}' → '{target}' "
            f"({connection_type}): {fields}"
        )
