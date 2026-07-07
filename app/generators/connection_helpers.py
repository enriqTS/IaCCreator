"""Utility for emitting Terraform variable blocks from connection-derived inputs."""

from __future__ import annotations

import logging

from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models._base import BaseServiceConfig
from app.models.ir_models import ResourceInstanceIR

logger = logging.getLogger(__name__)


def generate_connection_variables(instance: ResourceInstanceIR, renderer: HCLRenderer) -> str:
    """Emit variable blocks for connection-derived inputs.

    For each ConnectionInput declared in the config's get_connections_schema(),
    checks whether a matching ConnectionIR exists in instance.connections
    (matching source_service or target_service against source_service_type).

    If matched, emits a variable block. If unmatched, logs a warning and skips.

    Returns:
        A string containing the rendered HCL variable blocks, or empty string
        if no connection variables apply.
    """
    config = instance.config
    if not isinstance(config, BaseServiceConfig):
        return ""

    connection_inputs = type(config).get_connections_schema()
    if not connection_inputs:
        return ""

    parts: list[str] = []
    for conn_input in connection_inputs:
        # Check if there's a matching connection in the instance
        matched = any(
            c.source_service.value == conn_input.source_service_type
            or c.target_service.value == conn_input.source_service_type
            for c in instance.connections
        )
        if matched:
            parts.append(
                renderer.render_variable(
                    conn_input.tf_variable_name,
                    "string",
                    conn_input.description,
                )
            )
        else:
            logger.warning(
                "Unresolved connection input '%s' for instance '%s': "
                "no connection from service '%s'",
                conn_input.name,
                instance.name,
                conn_input.source_service_type,
            )

    return "\n".join(parts)
