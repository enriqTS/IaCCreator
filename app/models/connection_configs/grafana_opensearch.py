"""Grafana defaults select an index while query permissions cover the domain."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class GrafanaOpenSearchConfig(BaseConnectionConfig):
    index_name: str = ConnectionField(
        ...,
        label="Default index name",
        description="Existing concrete index for Grafana defaults; multi-search permissions cover the connected domain",
        validation=ValidationRule(pattern=r"^[a-z0-9][a-z0-9_.-]{0,254}$"),
    )
    time_field: str = ConnectionField(
        "@timestamp",
        label="Time field name",
        description="Date field used by Grafana queries in the selected index",
        validation=ValidationRule(pattern=r"^[A-Za-z_@][A-Za-z0-9_.@-]{0,254}$"),
    )
