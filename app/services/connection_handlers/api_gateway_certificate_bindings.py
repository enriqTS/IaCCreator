"""Resolve custom-domain ownership, certificate coverage, and stage mappings."""

import re

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.api_gateway_domains import ApiGatewayDomainBinding
from app.models.connection_configs.api_gateway_certificate import (
    ApiGatewayCertificateConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR, ResourceInstanceIR
from app.services.connection_handlers.api_gateway_stages import resolve_api_stage
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.private_certificate_bindings import (
    resolve_private_certificate_binding,
)


def _reject(connection: ConnectionIR, field: str, message: str) -> None:
    raise InvalidConnectionConfigError(
        connection.source_name,
        connection.target_name,
        connection.connection_type,
        [{"loc": (field,), "msg": message}],
    )


def _region(
    instance: ResourceInstanceIR, project: ProjectIR, override: str | None
) -> str:
    return override or instance.provider_region or project.global_config.provider_region


def certificate_covers_domain(domain: str, certificate_names: list[str]) -> bool:
    return any(
        domain == name
        or (
            name.startswith("*.")
            and domain.endswith(name[1:])
            and domain.count(".") == name.count(".")
        )
        for name in (value.strip().lower().rstrip(".") for value in certificate_names)
    )


def resolve_api_gateway_domains(
    gateway_name: str, project: ProjectIR
) -> list[ApiGatewayDomainBinding]:
    mappings: dict[tuple[str, str], ApiGatewayDomainBinding] = {}
    domains: dict[tuple[str, str], tuple[str, str]] = {}
    for connection in project.connections:
        if (
            connection.source_service != ServiceType.CERTIFICATE_MANAGER
            or connection.target_service != ServiceType.API_GATEWAY
            or connection.connection_type != "secures"
        ):
            continue
        request = ApiGatewayCertificateConfig.model_validate(
            connection.connection_config
        )
        gateway = BaseConnectionHandler._find_instance(connection.target_name, project)
        certificate = BaseConnectionHandler._find_instance(
            connection.source_name, project
        )
        config = gateway.config
        if config.protocol_type not in {"HTTP", "WEBSOCKET"}:
            _reject(
                connection,
                "domain_name",
                "Custom-domain connections support the modeled HTTP and WebSocket APIs",
            )
        if config.endpoint_type not in {
            None,
            "REGIONAL",
        } or config.security_policy not in {None, "TLS_1_2"}:
            _reject(
                connection,
                "domain_name",
                "API Gateway v2 custom domains require REGIONAL endpoints and TLS_1_2",
            )
        if config.protocol_type == "WEBSOCKET" and "/" in request.api_mapping_key:
            _reject(
                connection,
                "api_mapping_key",
                "WebSocket mappings support a single path segment",
            )
        names = [
            certificate.config.domain_name,
            *certificate.config.subject_alternative_names,
        ]
        if not certificate_covers_domain(request.domain_name, names):
            _reject(
                connection,
                "domain_name",
                "The certificate domain or SANs must cover the custom hostname; wildcards cover one label",
            )
        private = resolve_private_certificate_binding(certificate.name, project)
        if private is not None and (
            request.domain_name.startswith("*.")
            or config.mutual_tls_truststore_uri
            or config.mutual_tls_authentication
        ):
            _reject(
                connection,
                "domain_name",
                "Private certificates support concrete TLS domains; private-certificate mutual TLS requires an ownership-verification certificate not modeled by this connection",
            )
        if config.protocol_type == "WEBSOCKET" and (
            config.mutual_tls_truststore_uri or config.mutual_tls_authentication
        ):
            _reject(
                connection,
                "domain_name",
                "API Gateway mutual TLS is supported only for HTTP APIs",
            )
        if config.mutual_tls_authentication:
            _reject(
                connection,
                "domain_name",
                "Configure mutual TLS using the API truststore URI and optional version fields",
            )
        if (
            config.mutual_tls_truststore_version
            and not config.mutual_tls_truststore_uri
        ):
            _reject(
                connection,
                "domain_name",
                "A mutual TLS truststore version requires a truststore URI",
            )
        if config.mutual_tls_truststore_uri and not re.fullmatch(
            r"s3://[^/\s]+/[^\s]+", config.mutual_tls_truststore_uri
        ):
            _reject(
                connection,
                "domain_name",
                "Mutual TLS requires an S3 truststore URI with a bucket and object key",
            )
        stage = resolve_api_stage(connection, gateway, request.stage_name)
        binding = ApiGatewayDomainBinding(
            gateway.name,
            certificate.name,
            request.domain_name,
            stage,
            request.api_mapping_key,
        )
        for environment in project.environments:
            override = environment.variables.get("region")
            region = _region(gateway, project, override)
            cert_region = _region(certificate, project, override)
            if region != cert_region:
                raise CrossRegionConnectionError(
                    certificate.name,
                    cert_region,
                    gateway.name,
                    region,
                    connection.connection_type,
                )
            key = (region, request.domain_name)
            owner = (gateway.name, certificate.name)
            if key in domains and domains[key] != owner:
                _reject(
                    connection,
                    "domain_name",
                    "Each custom domain in an AWS Region must have one API module owner and one certificate",
                )
            domains[key] = owner
            for module in project.modules:
                for other in module.instances:
                    if (
                        other.service_type == ServiceType.API_GATEWAY
                        and other.config.custom_domain
                        and other.config.custom_domain.get("domain_name", "")
                        .strip()
                        .lower()
                        == request.domain_name
                        and _region(other, project, override) == region
                    ):
                        _reject(
                            connection,
                            "domain_name",
                            "This hostname already has a manually configured API custom-domain owner",
                        )
        if gateway.name == gateway_name:
            key = (request.domain_name, request.api_mapping_key)
            if key in mappings and mappings[key] != binding:
                _reject(
                    connection,
                    "api_mapping_key",
                    "Each domain mapping path can select only one stage and certificate",
                )
            mappings[key] = binding
    return [mappings[key] for key in sorted(mappings)]
