from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CloudTrailConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.CLOUDTRAIL] = ServiceType.CLOUDTRAIL
    trail_name: str = TerraformField("audit-trail", description="CloudTrail trail name")
    s3_bucket_name: str = TerraformField(
        "", description="S3 bucket receiving trail logs"
    )
    include_global_service_events: bool = TerraformField(
        True, description="Include global service events"
    )
    is_multi_region_trail: bool = TerraformField(
        True, description="Record events in every region"
    )
    enable_log_file_validation: bool = TerraformField(
        True, description="Enable log file integrity validation"
    )
