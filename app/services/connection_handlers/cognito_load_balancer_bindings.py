"""Resolve listener authentication independently of connection order."""

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.cognito_load_balancer import (
    CognitoLoadBalancerConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.models.load_balancer_authentication import CognitoListenerBinding
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


def _reject(connection: ConnectionIR, field: str, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": (field,), "msg": message}],
    )


def resolve_cognito_listener_bindings(
    load_balancer_name: str, project: ProjectIR
) -> dict[int, CognitoListenerBinding]:
    bindings = {}
    peers = [
        item
        for item in project.connections
        if item.target_name == load_balancer_name
        and item.source_service == ServiceType.COGNITO
        and item.target_service == ServiceType.LOAD_BALANCER
        and item.connection_type == "authenticates"
    ]
    if not peers:
        return bindings
    balancer = BaseConnectionHandler._find_instance(load_balancer_name, project)
    for connection in peers:
        config = CognitoLoadBalancerConfig.model_validate(connection.connection_config)
        pool = BaseConnectionHandler._find_instance(connection.source_name, project)
        for environment in project.environments:
            override = environment.variables.get("region")
            pool_region = (
                override
                or pool.provider_region
                or project.global_config.provider_region
            )
            balancer_region = (
                override
                or balancer.provider_region
                or project.global_config.provider_region
            )
            if pool_region != balancer_region:
                raise CrossRegionConnectionError(
                    pool.name,
                    pool_region,
                    balancer.name,
                    balancer_region,
                    connection.connection_type,
                )
        if balancer.config.load_balancer_type != "application":
            _reject(
                connection,
                "load_balancer_type",
                "Cognito requires an Application Load Balancer",
            )
        if not pool.config.domain_prefix:
            _reject(
                connection,
                "domain_prefix",
                "Configure a Cognito user-pool domain prefix before enabling ALB authentication",
            )
        listeners = [
            item
            for item in project.connections
            if item.source_name == load_balancer_name
            and item.target_service == ServiceType.TARGET_GROUP
            and item.connection_type == "forwards_to"
            and item.connection_config.get("port", 80) == config.listener_port
        ]
        if not listeners or any(
            item.connection_config.get("protocol", "HTTP") != "HTTPS"
            for item in listeners
        ):
            _reject(
                connection,
                "listener_port",
                "Select an existing HTTPS forwarding listener",
            )
        if len({item.target_name for item in listeners}) != 1:
            _reject(
                connection,
                "listener_port",
                "Authentication requires one unambiguous target group at the selected listener port",
            )
        target = listeners[0].target_name
        if any(
            item.source_name == load_balancer_name
            and item.target_service == ServiceType.TARGET_GROUP
            and item.connection_type == "forwards_to"
            and item.target_name != target
            and safe_identifier(item.target_name) == safe_identifier(target)
            for item in project.connections
        ):
            _reject(
                connection,
                "listener_port",
                "Target group names collide in the generated listener identifiers",
            )
        target_config = BaseConnectionHandler._find_instance(target, project).config
        if target_config.protocol not in {"HTTP", "HTTPS"}:
            _reject(
                connection,
                "listener_port",
                "Application listeners require an HTTP or HTTPS target group",
            )
        if not any(
            item.source_service == ServiceType.CERTIFICATE_MANAGER
            and item.target_name == load_balancer_name
            and item.connection_type == "secures"
            for item in project.connections
        ):
            _reject(
                connection,
                "listener_port",
                "HTTPS authentication requires a Certificate Manager connection",
            )
        if any(
            item.source_name == load_balancer_name
            and item.target_name == target
            and item.connection_type == "forwards_to"
            and item.connection_config.get("port", 80) != config.listener_port
            for item in project.connections
        ):
            _reject(
                connection,
                "listener_port",
                "The same target group cannot define multiple generated listeners",
            )
        binding = CognitoListenerBinding(connection.source_name, target, config)
        previous = bindings.get(config.listener_port)
        if previous is not None and previous != binding:
            _reject(
                connection,
                "listener_port",
                "A listener can have only one Cognito pool and one authentication configuration",
            )
        bindings[config.listener_port] = binding
    return bindings
