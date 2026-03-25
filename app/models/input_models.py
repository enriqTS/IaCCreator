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


class ResourceConfig(BaseModel):
    """Service-specific configuration for a resource instance."""

    # Lambda
    handler: Optional[str] = None
    runtime: Optional[str] = None
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    is_layer: bool = False
    # S3
    versioning: Optional[bool] = None
    # DynamoDB
    billing_mode: Optional[str] = None
    hash_key: Optional[str] = None
    hash_key_type: Optional[str] = None
    range_key: Optional[str] = None
    range_key_type: Optional[str] = None
    # API Gateway
    protocol_type: Optional[str] = None
    # CloudWatch
    retention_in_days: Optional[int] = None


class ResourceInstance(BaseModel):
    """A specific named resource within a service module."""

    name: str = Field(..., description="User-defined resource name, used as subfolder name")
    service_type: ServiceType
    config: ResourceConfig = Field(default_factory=ResourceConfig)

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


class EnvironmentConfig(BaseModel):
    """Configuration for a deployment environment."""

    name: str = Field(..., description="Environment name, e.g., dev, staging, prod")
    variables: dict[str, str] = Field(default_factory=dict)


class ArchitectureDescription(BaseModel):
    """Top-level input schema for the Terraform IaC Generator."""

    project_name: str = Field(
        ..., description="Root folder name for the generated project"
    )
    environments: list[EnvironmentConfig] = Field(..., min_length=1)
    resources: list[ResourceInstance] = Field(..., min_length=1)
    connections: list[Connection] = Field(default_factory=list)
