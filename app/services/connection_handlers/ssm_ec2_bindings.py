"""Each document-instance pair owns one association with consistent duplicate settings."""

import hashlib
from dataclasses import dataclass

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.ssm_ec2 import SsmEc2Config, string_parameters
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ssm_document import command_parameters


@dataclass(frozen=True)
class SsmEc2Binding:
    target: str
    key: str
    settings: SsmEc2Config
    parameters: dict[str, str]


def resolve_associations(
    connection: ConnectionIR, project: ProjectIR
) -> list[SsmEc2Binding]:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    peers = [
        c
        for c in project.connections
        if c.source_name == source.name
        and c.target_service == ServiceType.EC2
        and c.connection_type == "associates"
    ]
    try:
        declarations = command_parameters(source.config)
        bindings = {}
        for peer in peers:
            settings = SsmEc2Config.model_validate(peer.connection_config)
            parameters = string_parameters(settings.parameters_json)
            for key in parameters:
                if key not in declarations or declarations[key]["type"] != "String":
                    raise ValueError(
                        "Overrides must reference declared String parameters; StringList overrides are unsupported"
                    )
            if any(
                "default" not in declaration and key not in parameters
                for key, declaration in declarations.items()
            ):
                raise ValueError(
                    "Every required document parameter needs an explicit supported override"
                )
            if (
                len(source.config.content.encode("utf-8"))
                + len(settings.parameters_json.encode("utf-8"))
                > 65536
            ):
                raise ValueError(
                    "Document content and association parameters together must not exceed 64 KiB"
                )
            if (
                peer.target_name in bindings
                and bindings[peer.target_name].settings != settings
            ):
                raise ValueError(
                    "Repeated document-instance connections must agree on schedule, execution, and parameters"
                )
            identity = (
                f"{peer.source_id or source.name}:{peer.target_id or peer.target_name}"
            )
            bindings[peer.target_name] = SsmEc2Binding(
                peer.target_name,
                "assoc_" + hashlib.sha256(identity.encode()).hexdigest()[:16],
                settings,
                parameters,
            )
    except ValueError as exc:
        raise InvalidConnectionConfigError(
            source.name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("association",), "msg": str(exc)}],
        ) from exc
    for binding in bindings.values():
        target = BaseConnectionHandler._find_instance(binding.target, project)
        for environment in project.environments:
            override = environment.variables.get("region")
            source_region = (
                override
                or source.provider_region
                or project.global_config.provider_region
            )
            target_region = (
                override
                or target.provider_region
                or project.global_config.provider_region
            )
            if source_region != target_region:
                raise CrossRegionConnectionError(
                    source.name,
                    source_region,
                    target.name,
                    target_region,
                    connection.connection_type,
                )
    return [bindings[name] for name in sorted(bindings)]
