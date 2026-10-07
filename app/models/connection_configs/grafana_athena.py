"""Athena bindings select existing tables in the regional AWS Glue catalog."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

RESULT_LOCATION_PATTERN = (
    r"^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/(?:[A-Za-z0-9_-][A-Za-z0-9_.-]*/)+$"
)


class GrafanaAthenaConfig(BaseConnectionConfig):
    database_name: str = ConnectionField(
        ...,
        label="Glue database name",
        description="Existing database in the workgroup Region's AwsDataCatalog",
        validation=ValidationRule(pattern=r"^[a-z_][a-z0-9_]{0,254}$"),
    )
    table_name: str = ConnectionField(
        ...,
        label="Glue table name",
        description="Existing table; dataset S3 permissions remain separately configured",
        validation=ValidationRule(pattern=r"^[a-z_][a-z0-9_]{0,254}$"),
    )
