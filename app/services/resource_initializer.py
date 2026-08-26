"""Backend-owned resource naming and default derivation."""

from typing import Any

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType
from app.models.input_models._general import _get_cached_service_config_models


class ResourceInitializer:
    """Derive canonical initial values from service models and registries."""

    def initialize(
        self, service: ServiceType, existing_names: list[str]
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        if service not in GENERATOR_REGISTRY:
            raise ValueError("Service is not supported")
        return (
            self.default_name(service, existing_names),
            self.config_defaults(service),
            self.terraform_defaults(service),
        )

    @staticmethod
    def default_name(service: ServiceType, existing_names: list[str]) -> str:
        """Return the first available service-number name."""
        existing = set(existing_names)
        index = 1
        while f"{service.value}-{index}" in existing:
            index += 1
        return f"{service.value}-{index}"

    @staticmethod
    def config_defaults(service: ServiceType) -> dict[str, Any]:
        """Return optional typed config defaults for a service."""
        model = _get_cached_service_config_models().get(service)
        if model is None:
            return {}
        defaults: dict[str, Any] = {}
        for name, field in model.model_fields.items():
            if field.is_required():
                continue
            value = field.get_default(call_default_factory=True)
            if value is not None:
                defaults[name] = value
        return defaults

    @staticmethod
    def terraform_defaults(service: ServiceType) -> dict[str, Any]:
        """Return editor values derived from Terraform field metadata."""
        model = _get_cached_service_config_models().get(service)
        if model is None or not model.has_terraform_schema():
            return {}
        fallbacks: dict[str, Any] = {"string": "", "number": 0, "bool": False}
        return {
            field.name: field.default
            if field.default is not None
            else fallbacks[field.type]
            for field in model.get_variable_schema()
            if field.default is not None or field.type in fallbacks
        }
