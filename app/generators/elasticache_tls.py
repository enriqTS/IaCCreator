"""Guard Terraform overrides against unsupported standalone Memcached TLS settings."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.elasticache_config import (
    MEMCACHED_TLS_UNSUPPORTED_NODES,
    MEMCACHED_TLS_VERSION_PATTERN,
)


def tls_preconditions() -> list[dict]:
    renderer = HCLRenderer()
    version = renderer.render_expression(MEMCACHED_TLS_VERSION_PATTERN)
    unsupported = renderer.render_expression(MEMCACHED_TLS_UNSUPPORTED_NODES)
    return [
        {
            "condition": Expr(
                f'!var.transit_encryption_enabled || (var.engine == "memcached" && can(regex({version}, var.engine_version)))'
            ),
            "error_message": "Standalone cache TLS requires Memcached 1.6.12 or newer.",
        },
        {
            "condition": Expr(
                f'!var.transit_encryption_enabled || (length(trimspace(var.subnet_group_name)) > 0 && can(regex("^cache\\\\.[a-z][a-z0-9]*\\\\.[a-z0-9]+$", var.node_type)) && !can(regex({unsupported}, var.node_type)))'
            ),
            "error_message": "Memcached TLS requires VPC placement and a supported node type (not M1, M2, M3, R3, or T2).",
        },
    ]
