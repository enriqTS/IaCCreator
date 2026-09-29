"""Configuration for a workflow PutEvents task."""

import json

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class StepFunctionsEventBridgeConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )
    source: str = ConnectionField(
        "iaccreator.workflow",
        label="Event source",
        description="Custom event source; the aws. prefix is reserved for AWS services",
        validation=ValidationRule(pattern=r"^.{1,256}$"),
    )
    detail_type: str = ConnectionField(
        "Workflow Event",
        label="Detail type",
        description="Event type used by the target rule's event pattern",
        validation=ValidationRule(pattern=r"^.{1,128}$"),
    )
    detail_json: str | None = ConnectionField(
        None,
        label="Constant event detail",
        description="Optional JSON object; when omitted, the state input becomes the event detail",
    )

    @model_validator(mode="after")
    def validate_event(self):
        if (
            not self.source.strip()
            or self.source.startswith("aws.")
            or len(self.source) > 256
        ):
            raise ValueError(
                "Event source must be 1–256 characters and cannot use aws."
            )
        if not self.detail_type.strip() or len(self.detail_type) > 128:
            raise ValueError("Detail type must be 1–128 characters")
        if self.detail_json is not None:
            try:
                detail = json.loads(self.detail_json)
            except ValueError as error:
                raise ValueError("Constant event detail must be valid JSON") from error
            if not isinstance(detail, dict):
                raise ValueError("Constant event detail must be a JSON object")
        return self
