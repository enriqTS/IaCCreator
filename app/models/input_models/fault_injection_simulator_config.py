from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class FaultInjectionSimulatorConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.FAULT_INJECTION_SIMULATOR] = (
        ServiceType.FAULT_INJECTION_SIMULATOR
    )
    description: str = TerraformField(
        "Managed fault injection experiment", description="Experiment description"
    )
    role_arn: str = TerraformField(
        "", description="IAM role ARN used by the experiment"
    )
    action_name: str = TerraformField(
        "fault_action", description="Terraform action identifier"
    )
    action_id: str = TerraformField(
        "aws:ec2:stop-instances", description="AWS FIS action ID"
    )
