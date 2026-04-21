"""Input data models (Pydantic schemas) for the Terraform IaC Generator."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ServiceType(str, Enum):
    """Supported AWS service types."""

    LAMBDA = "lambda"
    S3 = "s3"
    API_GATEWAY = "api-gateway"
    DYNAMODB = "dynamodb"
    IAM = "iam"
    CLOUDWATCH = "cloudwatch"
    SNS = "sns"
    SQS = "sqs"


class ResourceConfig(BaseModel):
    """Service-specific configuration for a resource instance."""

    # Lambda
    handler: Optional[str] = None
    runtime: Optional[str] = None
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    is_layer: bool = False
    description: Optional[str] = None
    environment_variables: Optional[dict[str, str]] = None
    tags: Optional[dict[str, str]] = None
    layers: Optional[list[str]] = None
    architectures: Optional[str] = None
    ephemeral_storage_size: Optional[int] = None
    reserved_concurrent_executions: Optional[int] = None
    publish: Optional[bool] = None
    # S3
    versioning: Optional[bool] = None
    force_destroy: Optional[bool] = None
    object_lock_enabled: Optional[bool] = None
    acceleration_status: Optional[str] = None
    # DynamoDB
    billing_mode: Optional[str] = None
    hash_key: Optional[str] = None
    hash_key_type: Optional[str] = None
    range_key: Optional[str] = None
    range_key_type: Optional[str] = None
    read_capacity: Optional[int] = None
    write_capacity: Optional[int] = None
    point_in_time_recovery_enabled: Optional[bool] = None
    deletion_protection_enabled: Optional[bool] = None
    table_class: Optional[str] = None
    # API Gateway
    protocol_type: Optional[str] = None
    cors_configuration: Optional[dict] = None
    disable_execute_api_endpoint: Optional[bool] = None
    route_selection_expression: Optional[str] = None
    # CloudWatch
    retention_in_days: Optional[int] = None
    kms_key_id: Optional[str] = None
    log_group_class: Optional[str] = None
    # SNS
    display_name: Optional[str] = None
    fifo_topic: Optional[bool] = None
    content_based_deduplication: Optional[bool] = None  # shared with SQS
    kms_master_key_id: Optional[str] = None  # shared with CloudWatch
    # SQS
    visibility_timeout_seconds: Optional[int] = None
    message_retention_seconds: Optional[int] = None
    fifo_queue: Optional[bool] = None
    delay_seconds: Optional[int] = None
    max_message_size: Optional[int] = None


class ResourceInstance(BaseModel):
    """A specific named resource within a service module."""

    name: str = Field(..., description="User-defined resource name, used as subfolder name")
    service_type: ServiceType
    config: ResourceConfig = Field(default_factory=ResourceConfig)
    terraform_variables: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dynamodb_hash_key(self) -> "ResourceInstance":
        """DynamoDB resources must have hash_key in config."""
        if self.service_type == ServiceType.DYNAMODB and self.config.hash_key is None:
            raise ValueError(
                "DynamoDB resource must have 'hash_key' specified in config"
            )
        return self


class Connection(BaseModel):
    """A connection between two resource instances."""

    source: str = Field(..., description="Name of the source resource instance")
    target: str = Field(..., description="Name of the target resource instance")
    connection_type: str = Field(
        ..., description="e.g., 'triggers', 'reads_from', 'writes_to'"
    )
    connection_config: dict[str, str | int | float | bool] = Field(default_factory=dict)


class EnvironmentConfig(BaseModel):
    """Configuration for a deployment environment."""

    name: str = Field(..., description="Environment name, e.g., dev, staging, prod")
    variables: dict[str, str] = Field(default_factory=dict)


class GlobalTerraformConfig(BaseModel):
    """Project-level Terraform configuration for backend, provider, and version constraints."""

    backend_type: str = "local"
    backend_config: dict[str, str] = Field(default_factory=dict)
    provider_region: str = "us-east-1"
    provider_profile: str | None = None
    terraform_version: str | None = None
    aws_provider_version: str | None = None


class ArchitectureDescription(BaseModel):
    """Top-level input schema for the Terraform IaC Generator."""

    project_name: str = Field(
        ..., description="Root folder name for the generated project"
    )
    environments: list[EnvironmentConfig] = Field(..., min_length=1)
    resources: list[ResourceInstance] = Field(..., min_length=1)
    connections: list[Connection] = Field(default_factory=list)
    global_terraform_config: GlobalTerraformConfig = Field(default_factory=GlobalTerraformConfig)
