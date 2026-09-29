"""Selection of a GraphQL field for a direct Lambda resolver."""

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

_GRAPHQL_NAME = ValidationRule(pattern=r"^[_A-Za-z][_0-9A-Za-z]*$")


class AppSyncLambdaConfig(BaseConnectionConfig):
    type_name: str = ConnectionField(
        "Query",
        label="GraphQL type",
        description="Object type containing the field to resolve",
        validation=_GRAPHQL_NAME,
    )
    field_name: str = ConnectionField(
        ...,
        label="GraphQL field",
        description="Field on the selected object type to resolve with Lambda",
        validation=_GRAPHQL_NAME,
    )

    @model_validator(mode="after")
    def validate_names(self):
        if self.type_name.startswith("__") or self.field_name.startswith("__"):
            raise ValueError(
                "GraphQL introspection names starting with __ are reserved"
            )
        return self
