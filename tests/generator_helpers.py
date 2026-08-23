"""Shared helpers for building generator inputs across the generator test modules."""

from __future__ import annotations

import re
from typing import Any, get_args, get_origin

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import get_service_config_models
from app.models.ir_models import ResourceInstanceIR

VAR_REFERENCE = re.compile(r"var\.([A-Za-z_][A-Za-z0-9_]*)")
VARIABLE_DECLARATION = re.compile(r'variable\s+"([^"]+)"')


def _sample_for(annotation: Any, rule: Any) -> Any:
    """Pick a value satisfying a required field's type and any allowed_values rule."""
    if rule is not None and getattr(rule, "allowed_values", None):
        return rule.allowed_values[0]
    origin = get_origin(annotation)
    if origin is not None:
        args = [a for a in get_args(annotation) if a is not type(None)]
        annotation = args[0] if args else str
        if get_origin(annotation) is list:
            return []
        if get_origin(annotation) is dict:
            return {}
    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    if annotation is list:
        return []
    if annotation is dict:
        return {}
    return "probe"


def minimal_config_for(service_type: ServiceType) -> BaseServiceConfig:
    """Build the smallest valid config for a service by filling only required fields."""
    config_cls = get_service_config_models().get(service_type)
    if config_cls is None or not config_cls.has_terraform_schema():
        return BaseServiceConfig()

    kwargs: dict[str, Any] = {}
    for name, field in config_cls.model_fields.items():
        if not field.is_required():
            continue
        rule = next(
            (m for m in field.metadata if hasattr(m, "allowed_values")),
            None,
        )
        kwargs[name] = _sample_for(field.annotation, rule)
    return config_cls(**kwargs)


def make_instance(
    name: str, service_type: ServiceType, config: BaseServiceConfig
) -> ResourceInstanceIR:
    return ResourceInstanceIR(name=name, service_type=service_type, config=config)


def generated_files(service_type: ServiceType, name: str = "probe") -> dict[str, str]:
    """Render a service's three generated files from a minimal config."""
    generator = GENERATOR_REGISTRY[service_type]
    instance = make_instance(name, service_type, minimal_config_for(service_type))
    return {
        "resource": generator.generate_resource_tf(instance),
        "variables": generator.generate_variables_tf(instance),
        "outputs": generator.generate_outputs_tf(instance),
    }


# What a service needs beyond its required fields to be deployable, not merely valid
DEPLOYABLE_EXTRAS: dict[ServiceType, dict[str, Any]] = {
    ServiceType.LAMBDA: {
        "runtime": "python3.12",
        "handler": "main.handler",
        "filename": "function.zip",
    },
    ServiceType.API_GATEWAY: {"protocol_type": "HTTP"},
    ServiceType.DYNAMODB: {"hash_key": "id", "hash_key_type": "S"},
    ServiceType.EVENTBRIDGE: {"event_pattern": '{"source": ["aws.s3"]}'},
}


def connection_architecture(spec) -> dict:
    """Build the smallest two-resource architecture exercising one connection spec."""
    models = get_service_config_models()
    resources = []
    for name, service_type, rid in (
        ("source-resource", spec.source, "src"),
        ("target-resource", spec.target, "tgt"),
    ):
        config = minimal_config_for(service_type).model_dump(exclude_none=True)
        config.update(DEPLOYABLE_EXTRAS.get(service_type, {}))
        model = models.get(service_type)
        if model is not None:
            # Name every name-ish field so the module gets its required arguments
            for key in model.model_fields:
                if key == "name" or key.endswith("_name"):
                    config[key] = name
        config["service_type"] = service_type.value
        resources.append(
            {
                "id": rid,
                "name": name,
                "service_type": service_type.value,
                "config": config,
                "terraform_variables": {},
            }
        )

    return {
        "project_name": "connection-check",
        "environments": [{"name": "dev", "variables": {}}],
        "resources": resources,
        "connections": [
            {
                "source": "source-resource",
                "target": "target-resource",
                "source_id": "src",
                "target_id": "tgt",
                "connection_type": spec.connection_type,
                "connection_config": {},
            }
        ],
        "global_terraform_config": {
            "backend_type": "local",
            "backend_config": {},
            "provider_region": "us-east-1",
        },
    }
