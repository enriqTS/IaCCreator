"""Typed settings for EventBridge submissions to AWS Batch."""

from pydantic import StrictInt

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EventBridgeBatchConfig(BaseConnectionConfig):
    target_id: str | None = ConnectionField(
        None,
        label="Target Id",
        description="Identifier for this target within the rule",
        validation=ValidationRule(pattern=r"^[\w.\-]{1,64}$"),
    )
    job_definition_name: str = ConnectionField(
        ...,
        label="Job definition",
        description="Name of a Batch job definition node in this diagram",
    )
    job_name: str = ConnectionField(
        "eventbridge-job",
        label="Job name",
        description="Name assigned to submitted Batch jobs",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )
    array_size: StrictInt | None = ConnectionField(
        None,
        label="Array size",
        type="number",
        description="Number of child jobs for an array job",
        validation=ValidationRule(min=2, max=10000),
    )
    job_attempts: StrictInt | None = ConnectionField(
        None,
        label="Job attempts",
        type="number",
        description="Maximum attempts for a failed job",
        validation=ValidationRule(min=1, max=10),
    )
