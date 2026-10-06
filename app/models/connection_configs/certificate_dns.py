"""Public ACM DNS-validation record settings."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class CertificateDnsConfig(BaseConnectionConfig):
    ttl: int = ConnectionField(
        60,
        label="Validation record TTL",
        type="number",
        description="TTL in seconds for ACM validation CNAME records",
        validation=ValidationRule(min=1, max=2147483647),
    )
