"""GraphQL field and event metadata for an AppSync EventBridge resolver."""

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

_GRAPHQL_NAME = ValidationRule(pattern=r"^[_A-Za-z][_0-9A-Za-z]*$")


class AppSyncEventBridgeConfig(BaseConnectionConfig):
    field_name: str = ConnectionField(
        ...,
        label="GraphQL field",
        description="Mutation field that publishes an event",
        validation=_GRAPHQL_NAME,
    )
    type_name: str = ConnectionField(
        "Mutation",
        label="GraphQL type",
        description="Object type containing the publishing field",
        validation=_GRAPHQL_NAME,
    )
    event_source: str = ConnectionField(
        ...,
        label="Event source",
        description="Application event source, such as com.example.orders",
    )
    detail_type: str = ConnectionField(
        ...,
        label="Detail type",
        description="Event type used by EventBridge rules",
    )
    detail_argument: str = ConnectionField(
        "input",
        label="Detail argument",
        description="GraphQL input object sent as event detail",
        validation=_GRAPHQL_NAME,
    )

    @model_validator(mode="after")
    def validate_names(self):
        if self.field_name.startswith("__") or self.type_name.startswith("__"):
            raise ValueError(
                "GraphQL introspection names starting with __ are reserved"
            )
        if self.detail_argument.startswith("__"):
            raise ValueError(
                "GraphQL introspection names starting with __ are reserved"
            )
        if not self.event_source.strip() or len(self.event_source) > 256:
            raise ValueError("Event source must contain 1 to 256 characters")
        if self.event_source.startswith("aws."):
            raise ValueError("Event source prefix aws. is reserved")
        if not self.detail_type.strip() or len(self.detail_type) > 128:
            raise ValueError("Detail type must contain 1 to 128 characters")
        return self
