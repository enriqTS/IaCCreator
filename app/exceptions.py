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


class GeneratorConfigError(DomainError):
    """Raised when a generator receives a config instance of an unexpected type."""

    pass
