"""Amazon MWAA environment configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class MwaaConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MWAA] = ServiceType.MWAA
    execution_role_arn: str = TerraformField("", description="MWAA execution role ARN")
    source_bucket_arn: str = TerraformField(
        "", description="S3 bucket ARN containing workflow files"
    )
    dag_s3_path: str = TerraformField(
        "dags", description="DAG directory path in the source bucket"
    )
    subnet_ids: list[str] = TerraformField([], description="Two private subnet IDs")
    security_group_ids: list[str] = TerraformField(
        [], description="Environment security group IDs"
    )
    environment_class: str = TerraformField(
        "mw1.small", description="MWAA environment class"
    )
    max_workers: int = TerraformField(
        10, description="Maximum worker count", validation=ValidationRule(min=1)
    )
    min_workers: int = TerraformField(
        1, description="Minimum worker count", validation=ValidationRule(min=1)
    )
    webserver_access_mode: str = TerraformField(
        "PRIVATE_ONLY",
        description="Web server network access",
        options=[
            OptionEntry(value="PRIVATE_ONLY", label="Private only"),
            OptionEntry(value="PUBLIC_ONLY", label="Public"),
        ],
    )
    airflow_version: str | None = TerraformField(
        None, description="Optional Apache Airflow version"
    )
