"""Selection of a workflow placeholder for a connection-owned task."""

from pydantic import StrictInt

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class StepFunctionsSecretConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )


class StepFunctionsLambdaConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )


class StepFunctionsEcsConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )
    task_count: StrictInt = ConnectionField(
        1,
        label="Task count",
        description="Fargate tasks started by this workflow state",
        type="number",
        validation=ValidationRule(min=1, max=10),
    )


class StepFunctionsBatchConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )
    job_definition_name: str = ConnectionField(
        ...,
        label="Job definition",
        description="Name of a Batch job definition node in this diagram",
    )
    job_name: str = ConnectionField(
        "workflow-job",
        label="Job name",
        description="Name assigned to submitted Batch jobs",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )
    array_size: StrictInt | None = ConnectionField(
        None,
        label="Array size",
        description="Number of child jobs for an array job",
        type="number",
        validation=ValidationRule(min=2, max=10000),
    )
    job_attempts: StrictInt | None = ConnectionField(
        None,
        label="Job attempts",
        description="Maximum attempts for a failed job",
        type="number",
        validation=ValidationRule(min=1, max=10),
    )


class StepFunctionsSnsConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )
    message: str | None = ConnectionField(
        None,
        label="Constant message",
        description="Optional message text; when omitted, publish the JSON-encoded state input",
    )
    message_group_id: str | None = ConnectionField(
        None,
        label="FIFO message group ID",
        description="Required when publishing to a FIFO topic",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )
    message_deduplication_id: str | None = ConnectionField(
        None,
        label="FIFO deduplication ID",
        description="Optional fixed ID; otherwise use content-based deduplication or a generated UUID",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )


class StepFunctionsSqsConfig(BaseConnectionConfig):
    state_name: str = ConnectionField(
        "Pass",
        label="Pass state to replace",
        description="Existing top-level JSONPath Pass state; its transition and data paths are preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z][A-Za-z0-9 _-]{0,79}$"),
    )
    message: str | None = ConnectionField(
        None,
        label="Constant message",
        description="Optional message text; when omitted, send the JSON-encoded state input",
    )
    message_group_id: str | None = ConnectionField(
        None,
        label="FIFO message group ID",
        description="Required when sending to a FIFO queue",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )
    message_deduplication_id: str | None = ConnectionField(
        None,
        label="FIFO deduplication ID",
        description="Optional fixed ID; otherwise use content-based deduplication or a generated UUID",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )
