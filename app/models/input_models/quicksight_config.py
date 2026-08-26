"""Amazon QuickSight namespace configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class QuickSightConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.QUICKSIGHT] = ServiceType.QUICKSIGHT
    namespace_name: str = TerraformField(
        "default", description="QuickSight namespace name"
    )
    aws_account_id: str = TerraformField("", description="AWS account ID")
    identity_store: str = TerraformField(
        "QUICKSIGHT",
        description="Namespace identity store",
        options=[OptionEntry(value="QUICKSIGHT", label="QuickSight")],
    )
