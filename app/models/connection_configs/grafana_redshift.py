"""Redshift bindings select existing databases and non-administrator users."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

REDSHIFT_SELECTOR_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"


class GrafanaRedshiftConfig(BaseConnectionConfig):
    database_name: str = ConnectionField(
        ...,
        label="Database name",
        description="Existing Redshift database; database lifecycle is managed separately",
        validation=ValidationRule(pattern=REDSHIFT_SELECTOR_PATTERN),
    )
    database_user: str = ConnectionField(
        ...,
        label="Database user",
        description="Existing non-administrator user with separately configured SQL grants",
        validation=ValidationRule(pattern=REDSHIFT_SELECTOR_PATTERN),
    )
