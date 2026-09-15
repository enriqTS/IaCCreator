"""Named OpenSearch indexes constrain application HTTP access paths."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class OpenSearchIndexAccessConfig(BaseConnectionConfig):
    index_name: str = ConnectionField(
        ...,
        label="Index name",
        description="Explicit index name; wildcards, aliases, and index lists are not supported",
        validation=ValidationRule(pattern=r"^[a-z0-9][a-z0-9_.-]{0,254}$"),
    )
