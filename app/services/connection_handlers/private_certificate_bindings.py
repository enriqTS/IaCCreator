"""Validate issuing authorities and resolve private-certificate bindings."""

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.private_certificate import PrivateCertificateConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.models.private_certificate import (
    ECDSA_CA_KEYS,
    ECDSA_SIGNATURES,
    RSA_CA_KEYS,
    RSA_SIGNATURES,
    PrivateCertificateBinding,
)
from app.services.connection_handlers.base import BaseConnectionHandler


def _reject(connection: ConnectionIR, field: str, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": (field,), "msg": message}],
    )


def resolve_private_certificate_binding(
    certificate_name: str, project: ProjectIR
) -> PrivateCertificateBinding | None:
    peers = [
        item
        for item in project.connections
        if item.source_service == ServiceType.PRIVATE_CERTIFICATE_AUTHORITY
        and item.target_service == ServiceType.CERTIFICATE_MANAGER
        and item.target_name == certificate_name
        and item.connection_type == "issues_certificate"
    ]
    binding = None
    certificate = BaseConnectionHandler._find_instance(certificate_name, project)
    for connection in peers:
        if any(
            item.source_name == certificate_name
            and item.target_service == ServiceType.CLOUDFRONT
            and item.connection_type == "secures"
            for item in project.connections
        ):
            _reject(
                connection,
                "certificate",
                "CloudFront viewer certificates must be publicly trusted; this self-signed private CA cannot issue one",
            )
        authority = BaseConnectionHandler._find_instance(
            connection.source_name, project
        )
        config = authority.config
        request = PrivateCertificateConfig.model_validate(connection.connection_config)
        for environment in project.environments:
            override = environment.variables.get("region")
            ca_region = (
                override
                or authority.provider_region
                or project.global_config.provider_region
            )
            acm_region = (
                override
                or certificate.provider_region
                or project.global_config.provider_region
            )
            if ca_region != acm_region:
                raise CrossRegionConnectionError(
                    authority.name,
                    ca_region,
                    certificate.name,
                    acm_region,
                    connection.connection_type,
                )
        if config.usage_mode != "GENERAL_PURPOSE":
            _reject(
                connection,
                "usage_mode",
                "ACM-managed private certificates require a GENERAL_PURPOSE CA",
            )
        if config.key_algorithm not in RSA_CA_KEYS + ECDSA_CA_KEYS:
            _reject(
                connection,
                "key_algorithm",
                "This connection supports RSA 2048/3072/4096 and ECDSA P-256/P-384 certificate authorities",
            )
        signatures = (
            RSA_SIGNATURES if config.key_algorithm in RSA_CA_KEYS else ECDSA_SIGNATURES
        )
        if config.signing_algorithm not in signatures:
            _reject(
                connection,
                "signing_algorithm",
                "The CA signing algorithm must match its RSA or ECDSA key family",
            )
        if request.key_algorithm != "AUTO" and request.key_algorithm.startswith(
            "RSA_"
        ) != config.key_algorithm.startswith("RSA_"):
            _reject(
                connection,
                "key_algorithm",
                "The ACM certificate key must match the CA's RSA or ECDSA family",
            )
        current = PrivateCertificateBinding(authority.name, request.key_algorithm)
        if binding is not None and binding != current:
            _reject(
                connection,
                "key_algorithm",
                "An ACM certificate can have only one issuing CA and one key configuration",
            )
        binding = current
    return binding
