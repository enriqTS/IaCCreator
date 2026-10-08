"""ECS collection controls metadata frequency and optional local application scraping."""

from pydantic import StrictInt

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EcsPrometheusConfig(BaseConnectionConfig):
    collection_interval_seconds: StrictInt = ConnectionField(
        60,
        label="Collection interval (seconds)",
        type="number",
        validation=ValidationRule(min=10, max=3600),
    )
    application_metrics_port: StrictInt = ConnectionField(
        0,
        label="Application /metrics port (0 disables)",
        type="number",
        description="Optional plain HTTP /metrics endpoint reachable at 127.0.0.1 in the task",
        validation=ValidationRule(min=0, max=65535),
    )
