"""DynamoDB-specific configuration model."""

from typing import Literal, Optional

from pydantic import model_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class DynamoDBConfig(BaseServiceConfig):
    """DynamoDB-specific configuration."""

    service_type: Literal[ServiceType.DYNAMODB] = ServiceType.DYNAMODB
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

    @model_validator(mode="after")
    def validate_hash_key_required(self) -> "DynamoDBConfig":
        """DynamoDB resources must have hash_key specified."""
        if self.hash_key is None:
            raise ValueError(
                "DynamoDB resource must have 'hash_key' specified in config"
            )
        return self
