"""Managed EKS collection keeps AWS's scrape jobs and bounds the interval."""

from pydantic import StrictInt

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EksPrometheusConfig(BaseConnectionConfig):
    scrape_interval_seconds: StrictInt = ConnectionField(
        60,
        label="Scrape interval (seconds)",
        type="number",
        description="Global interval for AWS's default EKS scrape jobs",
        validation=ValidationRule(min=30, max=3600),
    )
