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
