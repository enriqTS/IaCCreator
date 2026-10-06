"""Resolved custom domains and their API stage mappings."""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class ApiGatewayDomainBinding:
    gateway_name: str
    certificate_name: str
    domain_name: str
    stage_name: str
    api_mapping_key: str

    @property
    def domain_resource(self) -> str:
        suffix = sha256(self.domain_name.encode()).hexdigest()[:12]
        return f"{self.gateway_name}_domain_{suffix}"

    @property
    def mapping_resource(self) -> str:
        suffix = sha256(self.api_mapping_key.encode()).hexdigest()[:12]
        return f"{self.domain_resource}_mapping_{suffix}"

    @property
    def certificate_input(self) -> str:
        return f"acm_{self.certificate_name}_certificate_arn"

    @property
    def certificate_names_input(self) -> str:
        return f"acm_{self.certificate_name}_certificate_names"
