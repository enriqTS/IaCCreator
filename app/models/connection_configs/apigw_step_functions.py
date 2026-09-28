"""HTTP API routes that start a connected Step Functions workflow."""

from typing import Any

from pydantic import Field

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import (
    ConnectionField,
    LinkedEntry,
    LinkedEntryField,
)
from app.models.input_models._metadata import OptionEntry, ValidationRule


class ApiGatewayStepFunctionsConfig(BaseConnectionConfig):
    route_path: str | None = ConnectionField(
        None,
        label="Route",
        description="POST route that starts the workflow",
        type="linkedSelect",
        validation=ValidationRule(pattern=r"^/[\w\-/{}\$]*$"),
        linked=LinkedEntry(
            config_path="routes",
            display_key="path",
            create_template={"methods": ["POST"], "path": "", "integration_name": ""},
            target_name_key="integration_name",
            target_id_key="integration_id",
            entry_fields=[
                LinkedEntryField(
                    key="methods",
                    label="Methods",
                    type="multiSelect",
                    default=["POST"],
                    options=[OptionEntry(value="POST", label="POST")],
                )
            ],
        ),
    )
    routes: list[dict[str, Any]] = Field(default_factory=list)
