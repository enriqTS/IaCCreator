from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AwsConfigConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.AWS_CONFIG] = ServiceType.AWS_CONFIG
    recorder_name: str = TerraformField(
        "default", description="Configuration recorder name"
    )
    role_arn: str = TerraformField("", description="IAM role ARN used by AWS Config")
    s3_bucket_name: str = TerraformField("", description="S3 delivery bucket name")
    all_supported: bool = TerraformField(
        True, description="Record every supported resource type"
    )
    include_global_resource_types: bool = TerraformField(
        True, description="Include global resource types"
    )
