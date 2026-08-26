"""AWS Step Functions state machine configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField

_DEFAULT_DEFINITION = '{"StartAt":"Pass","States":{"Pass":{"Type":"Pass","End":true}}}'


class StepFunctionsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.STEP_FUNCTIONS] = ServiceType.STEP_FUNCTIONS
    role_arn: str = TerraformField("", description="IAM execution role ARN")
    definition: str = TerraformField(
        _DEFAULT_DEFINITION, description="Amazon States Language definition as JSON"
    )
    state_machine_type: str = TerraformField(
        "STANDARD",
        description="Workflow execution type",
        options=[
            OptionEntry(value="STANDARD", label="Standard"),
            OptionEntry(value="EXPRESS", label="Express"),
        ],
    )
    publish: bool = TerraformField(
        False, description="Publish a version when the state machine changes"
    )
