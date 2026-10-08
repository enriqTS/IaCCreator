"""Shared stage selection validates Terraform identity and deployment settings."""

import re

from app.exceptions import InvalidConnectionConfigError
from app.generators.api_gateway._support import sanitize_route_name
from app.models.ir_models import ConnectionIR, ResourceInstanceIR


def _reject(connection: ConnectionIR, field: str, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": (field,), "msg": message}],
    )


def resolve_api_stage(
    connection: ConnectionIR,
    gateway: ResourceInstanceIR,
    stage_name: str,
) -> str:
    config = gateway.config
    stages = config.stages or []
    if config.protocol_type == "WEBSOCKET" and not stages:
        _reject(
            connection,
            "stage_name",
            "Configure a named WebSocket stage before mapping a custom domain",
        )
    names = [item.get("name", "$default") for item in stages] or ["$default"]
    for name in names:
        if not isinstance(name, str) or (
            name != "$default" and not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", name)
        ):
            _reject(
                connection,
                "stage_name",
                "Configured stage names must use letters, numbers, underscores, or hyphens",
            )
    identifiers = [sanitize_route_name(name) for name in names]
    if len(set(identifiers)) != len(identifiers):
        _reject(
            connection,
            "stage_name",
            "Configured stage names must produce distinct Terraform identifiers",
        )
    if any(
        "auto_deploy" in item and not isinstance(item["auto_deploy"], bool)
        for item in stages
    ):
        _reject(
            connection, "stage_name", "Stage automatic deployment must be a boolean"
        )
    if config.protocol_type == "WEBSOCKET" and (
        "$default" in names or any(item.get("auto_deploy", False) for item in stages)
    ):
        _reject(
            connection,
            "stage_name",
            "WebSocket APIs require named stages without automatic deployment",
        )
    selected = stage_name or names[0]
    if selected not in names:
        _reject(
            connection, "stage_name", "Select a stage configured on the connected API"
        )
    return selected
