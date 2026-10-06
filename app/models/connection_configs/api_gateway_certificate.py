"""Regional API custom-domain and stage mapping settings."""

import re

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField


class ApiGatewayCertificateConfig(BaseConnectionConfig):
    domain_name: str = ConnectionField(
        ...,
        label="Custom domain name",
        placeholder="api.example.com",
        description="DNS hostname covered by the connected ACM certificate",
    )
    stage_name: str = ConnectionField(
        "",
        label="API stage",
        description="Empty selects the first configured stage, or the HTTP default stage",
    )
    api_mapping_key: str = ConnectionField(
        "",
        label="API mapping path",
        description="Empty maps the domain root; HTTP mappings can use paths such as orders/v1",
    )

    @field_validator("domain_name", mode="before")
    @classmethod
    def normalize_domain(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("domain_name")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        hostname = value[2:] if value.startswith("*.") else value
        labels = hostname.split(".")
        if (
            len(value) > 253
            or len(labels) < 2
            or labels[-1].isdigit()
            or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels
            )
        ):
            raise ValueError(
                "Use a DNS hostname or leading wildcard without a scheme, port, or path"
            )
        return value

    @field_validator("stage_name", "api_mapping_key")
    @classmethod
    def validate_selector(cls, value: str, info) -> str:
        if info.field_name == "stage_name":
            if (
                value
                and value != "$default"
                and not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", value)
            ):
                raise ValueError("Use an API stage name or $default")
        elif len(value) > 300 or (
            value
            and (
                not re.fullmatch(r"[a-zA-Z0-9$_.+!*'()/-]+", value)
                or any(not part for part in value.split("/"))
            )
        ):
            raise ValueError(
                "Use an API mapping path of at most 300 characters without empty segments or surrounding slashes"
            )
        return value
