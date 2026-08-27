from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class DataSyncConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.DATASYNC] = ServiceType.DATASYNC
    task_name: str = TerraformField("data-transfer", description="DataSync task name")
    source_location_arn: str = TerraformField(
        "", description="ARN of the source DataSync location"
    )
    destination_location_arn: str = TerraformField(
        "", description="ARN of the destination DataSync location"
    )
    verify_mode: str = TerraformField(
        "ONLY_FILES_TRANSFERRED",
        description="Data verification mode",
        options=[
            OptionEntry(value="ONLY_FILES_TRANSFERRED", label="Transferred files"),
            OptionEntry(
                value="POINT_IN_TIME_CONSISTENT", label="Point-in-time consistent"
            ),
            OptionEntry(value="NONE", label="None"),
        ],
    )
    overwrite_mode: str = TerraformField(
        "ALWAYS",
        description="Destination overwrite behavior",
        options=[
            OptionEntry(value="ALWAYS", label="Always overwrite"),
            OptionEntry(value="NEVER", label="Never overwrite"),
        ],
    )
    tags: dict[str, str] = TerraformField(default_factory=dict, description="Task tags")
