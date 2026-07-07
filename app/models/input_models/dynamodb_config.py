"""DynamoDB-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import model_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
    VisibleWhen,
)


class DynamoDBConfig(BaseServiceConfig):
    """DynamoDB-specific configuration."""

    service_type: Literal[ServiceType.DYNAMODB] = ServiceType.DYNAMODB

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "table_name",
        "billing_mode",
        "table_class",
        "hash_key",
        "hash_key_type",
        "range_key",
        "range_key_type",
        "read_capacity",
        "write_capacity",
        "tags",
        "point_in_time_recovery_enabled",
        "deletion_protection_enabled",
    )

    # ── General ───────────────────────────────────────────────────────
    table_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the DynamoDB table",
    )
    billing_mode: str | None = TerraformField(
        "PAY_PER_REQUEST",
        group="General",
        description="Billing mode for read/write throughput",
        options=[
            OptionEntry(value="PAY_PER_REQUEST", label="On-Demand (PAY_PER_REQUEST)"),
            OptionEntry(value="PROVISIONED", label="Provisioned"),
        ],
    )
    table_class: str | None = TerraformField(
        "STANDARD",
        group="General",
        description="Storage class for the DynamoDB table",
        options=[
            OptionEntry(value="STANDARD", label="Standard"),
            OptionEntry(
                value="STANDARD_INFREQUENT_ACCESS",
                label="Standard - Infrequent Access",
            ),
        ],
    )

    # ── Key Schema ────────────────────────────────────────────────────
    hash_key: str | None = TerraformField(
        None,
        group="Key Schema",
        description="Attribute name for the partition (hash) key",
    )
    hash_key_type: str | None = TerraformField(
        "S",
        group="Key Schema",
        description="Attribute type for the partition (hash) key",
        options=[
            OptionEntry(value="S", label="String"),
            OptionEntry(value="N", label="Number"),
            OptionEntry(value="B", label="Binary"),
        ],
    )
    range_key: str | None = TerraformField(
        None,
        group="Key Schema",
        description="Attribute name for the sort (range) key",
    )
    range_key_type: str | None = TerraformField(
        "S",
        group="Key Schema",
        description="Attribute type for the sort (range) key",
        options=[
            OptionEntry(value="S", label="String"),
            OptionEntry(value="N", label="Number"),
            OptionEntry(value="B", label="Binary"),
        ],
    )

    # ── Capacity ──────────────────────────────────────────────────────
    read_capacity: int | None = TerraformField(
        5,
        group="Capacity",
        description="Provisioned read capacity units",
        validation=ValidationRule(min=1, max=40000),
        visible_when=VisibleWhen(field="billing_mode", equals="PROVISIONED"),
    )
    write_capacity: int | None = TerraformField(
        5,
        group="Capacity",
        description="Provisioned write capacity units",
        validation=ValidationRule(min=1, max=40000),
        visible_when=VisibleWhen(field="billing_mode", equals="PROVISIONED"),
    )

    # ── Metadata ──────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the DynamoDB table",
        tf_type="map",
    )
    point_in_time_recovery_enabled: bool | None = TerraformField(
        False,
        group="Metadata",
        description="Enable point-in-time recovery for the table",
    )
    deletion_protection_enabled: bool | None = TerraformField(
        False,
        group="Metadata",
        description="Enable deletion protection for the table",
    )

    @model_validator(mode="after")
    def validate_hash_key_required(self) -> "DynamoDBConfig":
        """DynamoDB resources must have hash_key specified."""
        if self.hash_key is None:
            raise ValueError(
                "DynamoDB resource must have 'hash_key' specified in config"
            )
        return self
