"""Helpers shared by the API Gateway sub-generators."""

import re

from app.generators.base import get_typed_config
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def resolve_config(instance: ResourceInstanceIR) -> ApiGatewayConfig:
    """Resolve an instance's config, tolerating a duck-typed stand-in."""
    try:
        return get_typed_config(instance, ApiGatewayConfig)
    except Exception:
        return instance.config  # type: ignore[return-value]


def sanitize_route_name(name: str) -> str:
    """Turn a route key into a Terraform-safe resource name."""
    sanitized = (
        name.replace("$", "").replace("/", "_").replace("{", "").replace("}", "")
    )
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")
