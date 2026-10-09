"""Workflow logging defaults to event history without execution payload data."""

from pydantic import StrictBool

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule

ROLE_ARN_PATTERN = (
    r"^arn:[^:]+:iam::[0-9]{12}:role/([A-Za-z0-9+=,.@_/-]+/)?[A-Za-z0-9+=,.@_-]{1,64}$"
)


class StepFunctionsLogsConfig(BaseConnectionConfig):
    level: str = ConnectionField(
        "ALL",
        label="Execution log level",
        type="select",
        options=[
            OptionEntry(value=value, label=value) for value in ("ALL", "ERROR", "FATAL")
        ],
        validation=ValidationRule(allowed_values=["ALL", "ERROR", "FATAL"]),
    )
    include_execution_data: StrictBool = ConnectionField(
        False,
        label="Include execution payloads",
        type="boolean",
        description="Include state inputs and outputs, which can contain sensitive data",
    )
