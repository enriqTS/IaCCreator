"""Stable ownership of ACM validation records."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.ir_models import ProjectIR


def dns_name(value: str, *, zone: bool = False) -> str:
    name = value.strip().lower()
    if zone:
        name = name.removesuffix(".")
    elif name.startswith("*."):
        name = name[2:]
    labels = name.split(".")
    if (
        len(name) > 253
        or (not zone and len(value.strip()) > 253)
        or len(labels) < 2
        or labels[-1].isdigit()
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        )
    ):
        raise ValueError(
            "Use a DNS hostname, with a leading wildcard only for certificates"
        )
    return name


@dataclass(frozen=True)
class CertificateDnsRecord:
    zone_name: str
    zone_domain: str
    domain: str
    certificate_name: str
    ttl: int


@dataclass(frozen=True)
class CertificateDnsBinding:
    certificate_name: str
    records: tuple[CertificateDnsRecord, ...]


def has_dns_validation(certificate_name: str, project: "ProjectIR") -> bool:
    from app.models.input_models import ServiceType

    return any(
        item.source_service == ServiceType.ROUTE53
        and item.target_service == ServiceType.CERTIFICATE_MANAGER
        and item.target_name == certificate_name
        and item.connection_type == "validates_certificate"
        for item in project.connections
    )
