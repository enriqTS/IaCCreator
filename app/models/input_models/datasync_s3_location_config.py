"""Reusable DataSync S3 transfer location configuration."""

from typing import Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class DataSyncS3LocationConfig(BaseServiceConfig):
    _managed_bucket: bool = PrivateAttr(default=False)
    service_type: Literal[ServiceType.DATASYNC_S3_LOCATION] = (
        ServiceType.DATASYNC_S3_LOCATION
    )
    s3_bucket_arn: str = TerraformField("", description="S3 bucket ARN")
    bucket_access_role_arn: str = TerraformField(
        "", description="External role trusted by DataSync"
    )
    subdirectory: str = TerraformField(
        "/",
        description="S3 location path",
        validation=ValidationRule(pattern=r"^/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]*$"),
    )
    access: str = TerraformField(
        "read",
        description="Source read access or destination read/write access",
        validation=ValidationRule(allowed_values=["read", "write"]),
    )
