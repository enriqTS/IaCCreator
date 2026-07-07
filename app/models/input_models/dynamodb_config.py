"""DynamoDB-specific configuration model."""

from typing import Literal

from pydantic import model_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class DynamoDBConfig(BaseServiceConfig):
    """DynamoDB-specific configuration."""

    service_type: Literal[ServiceType.DYNAMODB] = ServiceType.DYNAMODB
    billing_mode: str | None = None
    hash_key: str | None = None
    hash_key_type: str | None = None
    range_key: str | None = None
    range_key_type: str | None = None
    read_capacity: int | None = None
    write_capacity: int | None = None
    point_in_time_recovery_enabled: bool | None = None
    deletion_protection_enabled: bool | None = None
    table_class: str | None = None

    @model_validator(mode="after")
    def validate_hash_key_required(self) -> "DynamoDBConfig":
        """DynamoDB resources must have hash_key specified."""
        if self.hash_key is None:
            raise ValueError(
                "DynamoDB resource must have 'hash_key' specified in config"
            )
        return self
