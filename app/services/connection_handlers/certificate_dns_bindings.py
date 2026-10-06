"""Resolve hosted-zone coverage and shared validation-record ownership."""

from app.exceptions import InvalidConnectionConfigError
from app.models.certificate_dns import (
    CertificateDnsBinding,
    CertificateDnsRecord,
    dns_name,
)
from app.models.connection_configs.certificate_dns import CertificateDnsConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
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


def resolve_certificate_dns(project: ProjectIR) -> tuple[CertificateDnsBinding, ...]:
    peers = sorted(
        (
            item
            for item in project.connections
            if item.source_service == ServiceType.ROUTE53
            and item.target_service == ServiceType.CERTIFICATE_MANAGER
            and item.connection_type == "validates_certificate"
        ),
        key=lambda item: (item.target_name, item.source_name),
    )
    zones = {}
    certificates = {}
    requests = {}
    for connection in peers:
        zone = BaseConnectionHandler._find_instance(connection.source_name, project)
        certificate = BaseConnectionHandler._find_instance(
            connection.target_name, project
        )
        request = CertificateDnsConfig.model_validate(connection.connection_config)
        private_association = any(
            item.source_service == ServiceType.VPC
            and item.target_name == zone.name
            and item.connection_type == "contains"
            for item in project.connections
        )
        if zone.config.private_zone or private_association:
            _reject(
                connection,
                "private_zone",
                "ACM DNS validation requires a public hosted zone",
            )
        if resolve_private_certificate_binding(certificate.name, project) is not None:
            _reject(
                connection,
                "certificate",
                "Private CA certificates do not use public DNS validation",
            )
        if certificate.config.validation_method != "DNS":
            _reject(
                connection,
                "validation_method",
                "Select DNS validation on the connected ACM certificate",
            )
        try:
            zones[zone.name] = dns_name(zone.config.zone_name, zone=True)
            certificates[certificate.name] = tuple(
                sorted(
                    {
                        dns_name(name)
                        for name in [
                            certificate.config.domain_name,
                            *certificate.config.subject_alternative_names,
                        ]
                    }
                )
            )
        except ValueError as error:
            _reject(connection, "domain_name", str(error))
        key = (certificate.name, zone.name)
        if key in requests and requests[key] != request.ttl:
            _reject(
                connection,
                "ttl",
                "Repeated zone/certificate connections must use the same TTL",
            )
        requests[key] = request.ttl

    records = {}
    assignments = {}
    for certificate, domains in sorted(certificates.items()):
        available = {
            zone: ttl for (name, zone), ttl in requests.items() if name == certificate
        }
        for domain in domains:
            matches = [
                zone
                for zone in available
                if domain == zones[zone] or domain.endswith(f".{zones[zone]}")
            ]
            connection = next(item for item in peers if item.target_name == certificate)
            if not matches:
                _reject(
                    connection,
                    "domain_name",
                    f"Connect a public hosted zone covering every certificate name; {domain} is uncovered",
                )
            specificity = max(len(zones[zone]) for zone in matches)
            matches = [zone for zone in matches if len(zones[zone]) == specificity]
            if len(matches) != 1:
                _reject(
                    connection,
                    "zone_name",
                    f"Multiple connected hosted zones claim {domain}",
                )
            zone = matches[0]
            record = CertificateDnsRecord(
                zone, zones[zone], domain, certificate, available[zone]
            )
            if domain in records:
                previous = records[domain]
                if (previous.zone_name, previous.ttl) != (zone, available[zone]):
                    _reject(
                        connection,
                        "zone_name",
                        f"Certificates sharing {domain} must use one hosted zone and TTL",
                    )
                record = previous
            records[domain] = record
            assignments.setdefault(certificate, []).append(record)
    return tuple(
        CertificateDnsBinding(name, tuple(assigned))
        for name, assigned in sorted(assignments.items())
    )
