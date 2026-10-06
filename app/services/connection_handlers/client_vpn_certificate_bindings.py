"""Resolve certificate roles and reject incompatible Client VPN bindings."""

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.client_vpn_certificate import (
    ClientVpnCertificateConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.private_certificate_bindings import (
    resolve_private_certificate_binding,
)

ROLE_FIELDS = {
    "server": ("server_certificate_arn",),
    "client_trust": ("root_certificate_chain_arn",),
    "both": ("server_certificate_arn", "root_certificate_chain_arn"),
}


def _reject(connection: ConnectionIR, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": ("certificate_role",), "msg": message}],
    )


def resolve_client_vpn_certificates(
    endpoint_name: str, project: ProjectIR
) -> dict[str, str]:
    endpoint = BaseConnectionHandler._find_instance(endpoint_name, project)
    bindings: dict[str, str] = {}
    for connection in project.connections:
        if (
            connection.source_service != ServiceType.CERTIFICATE_MANAGER
            or connection.target_service != ServiceType.CLIENT_VPN
            or connection.target_name != endpoint_name
            or connection.connection_type != "secures"
        ):
            continue
        request = ClientVpnCertificateConfig.model_validate(
            connection.connection_config
        )
        certificate = BaseConnectionHandler._find_instance(
            connection.source_name, project
        )
        private = resolve_private_certificate_binding(certificate.name, project)
        if request.certificate_role != "server" and private is None:
            _reject(
                connection,
                "Client CA references require a managed private certificate; public ACM certificates cannot authenticate VPN clients",
            )
        if private is not None:
            authority = BaseConnectionHandler._find_instance(
                private.authority_name, project
            )
            if not authority.config.key_algorithm.startswith(
                "RSA_"
            ) or private.key_algorithm not in {"AUTO", "RSA_2048"}:
                _reject(
                    connection,
                    "Client VPN certificates require RSA 2048 keys; ECDSA certificates are unsupported",
                )
        for environment in project.environments:
            override = environment.variables.get("region")
            cert_region = (
                override
                or certificate.provider_region
                or project.global_config.provider_region
            )
            endpoint_region = (
                override
                or endpoint.provider_region
                or project.global_config.provider_region
            )
            if cert_region != endpoint_region:
                raise CrossRegionConnectionError(
                    certificate.name,
                    cert_region,
                    endpoint.name,
                    endpoint_region,
                    connection.connection_type,
                )
        for field in ROLE_FIELDS[request.certificate_role]:
            if field in bindings and bindings[field] != certificate.name:
                _reject(
                    connection,
                    "Each Client VPN certificate role can reference only one ACM certificate",
                )
            bindings[field] = certificate.name
    return dict(sorted(bindings.items()))
