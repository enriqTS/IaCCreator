"""Stage logging ownership resolves independently of connection processing order."""

from dataclasses import dataclass

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.api_gateway_logs import ApiGatewayLogsConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.api_gateway_stages import resolve_api_stage
from app.services.connection_handlers.base import BaseConnectionHandler


@dataclass(frozen=True)
class ApiGatewayLogBinding:
    stage_name: str
    log_group_name: str
    log_format: str


def _reject(connection: ConnectionIR, field: str, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": (field,), "msg": message}],
    )


def resolve_api_access_logs(
    gateway_name: str, project: ProjectIR
) -> list[ApiGatewayLogBinding]:
    bindings: dict[str, ApiGatewayLogBinding] = {}
    gateway = BaseConnectionHandler._find_instance(gateway_name, project)
    config = gateway.config
    for connection in project.connections:
        if not (
            connection.source_name == gateway_name
            and connection.source_service == ServiceType.API_GATEWAY
            and connection.target_service == ServiceType.CLOUDWATCH
            and connection.connection_type == "logs_to"
        ):
            continue
        request = ApiGatewayLogsConfig.model_validate(connection.connection_config)
        if config.protocol_type != "HTTP":
            _reject(
                connection,
                "protocol_type",
                "Managed access-log connections currently support HTTP APIs; WebSocket logging requires separately owned regional account permissions",
            )
        stage = resolve_api_stage(connection, gateway, request.stage_name)
        stage_config = next(
            (
                item
                for item in config.stages or []
                if item.get("name", "$default") == stage
            ),
            {},
        )
        if (
            config.access_log_destination_arn is not None
            or stage_config.get("access_log_destination_arn") is not None
            or stage_config.get("access_logging_enabled", False)
        ):
            _reject(
                connection,
                "stage_name",
                "Remove the selected stage's manual access-log destination or locally generated log group before adding a managed logging connection",
            )
        if (
            config.access_log_format is not None
            or stage_config.get("access_log_format") is not None
        ):
            _reject(
                connection,
                "log_format",
                "Configure the selected stage's access-log format on its managed connection",
            )
        group = BaseConnectionHandler._find_instance(connection.target_name, project)
        for environment in project.environments:
            override = environment.variables.get("region")
            source_region = (
                override
                or gateway.provider_region
                or project.global_config.provider_region
            )
            target_region = (
                override
                or group.provider_region
                or project.global_config.provider_region
            )
            if source_region != target_region:
                raise CrossRegionConnectionError(
                    gateway.name,
                    source_region,
                    group.name,
                    target_region,
                    connection.connection_type,
                )
        binding = ApiGatewayLogBinding(stage, group.name, request.log_format)
        if stage in bindings and bindings[stage] != binding:
            _reject(
                connection,
                "stage_name",
                "Each HTTP API stage can use only one managed log group and format",
            )
        bindings[stage] = binding
    return [bindings[name] for name in sorted(bindings)]
