"""DynamoDB-specific configuration model."""

from typing import ClassVar, Literal

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
        # General
        "table_name",
        "billing_mode",
        "table_class",
        # Key Schema
        "hash_key",
        "hash_key_type",
        "range_key",
        "range_key_type",
        # Capacity
        "read_capacity",
        "write_capacity",
        "on_demand_max_read_request_units",
        "on_demand_max_write_request_units",
        # Streams
        "stream_enabled",
        "stream_view_type",
        # TTL
        "ttl_enabled",
        "ttl_attribute_name",
        # Indexes
        "global_secondary_indexes",
        "local_secondary_indexes",
        # Encryption
        "server_side_encryption_enabled",
        "server_side_encryption_kms_key_arn",
        # Global Tables
        "replica_regions",
        # Metadata
        "tags",
        "point_in_time_recovery_enabled",
        "deletion_protection_enabled",
    )

    # ── General ───────────────────────────────────────────────────────
    table_name: str = TerraformField(
        ...,
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
    hash_key: str = TerraformField(
        ...,
        group="Key Schema",
        description="Attribute name for the partition (hash) key",
    )
    hash_key_type: str = TerraformField(
        ...,
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
    on_demand_max_read_request_units: int | None = TerraformField(
        None,
        group="Capacity",
        description="Maximum read request units for on-demand capacity mode",
        visible_when=VisibleWhen(field="billing_mode", equals="PAY_PER_REQUEST"),
    )
    on_demand_max_write_request_units: int | None = TerraformField(
        None,
        group="Capacity",
        description="Maximum write request units for on-demand capacity mode",
        visible_when=VisibleWhen(field="billing_mode", equals="PAY_PER_REQUEST"),
    )

    # ── Streams ───────────────────────────────────────────────────────
    stream_enabled: bool | None = TerraformField(
        None,
        group="Streams",
        description="Enable DynamoDB Streams on the table",
    )
    stream_view_type: str | None = TerraformField(
        None,
        group="Streams",
        description="Type of information written to the stream",
        options=[
            OptionEntry(value="NEW_IMAGE", label="New Image"),
            OptionEntry(value="OLD_IMAGE", label="Old Image"),
            OptionEntry(value="NEW_AND_OLD_IMAGES", label="New and Old Images"),
            OptionEntry(value="KEYS_ONLY", label="Keys Only"),
        ],
        visible_when=VisibleWhen(field="stream_enabled", equals=True),
    )

    # ── TTL ───────────────────────────────────────────────────────────
    ttl_enabled: bool | None = TerraformField(
        None,
        group="TTL",
        description="Enable Time to Live (TTL) for the table",
    )
    ttl_attribute_name: str | None = TerraformField(
        None,
        group="TTL",
        description="Name of the TTL attribute",
        visible_when=VisibleWhen(field="ttl_enabled", equals=True),
    )

    # ── Indexes ───────────────────────────────────────────────────────
    global_secondary_indexes: list[dict] | None = TerraformField(
        None,
        group="Indexes",
        description="List of global secondary index definitions",
        tf_type="list",
    )
    local_secondary_indexes: list[dict] | None = TerraformField(
        None,
        group="Indexes",
        description="List of local secondary index definitions",
        tf_type="list",
    )

    # ── Encryption ────────────────────────────────────────────────────
    server_side_encryption_enabled: bool | None = TerraformField(
        None,
        group="Encryption",
        description="Enable server-side encryption with a KMS key",
    )
    server_side_encryption_kms_key_arn: str | None = TerraformField(
        None,
        group="Encryption",
        description="ARN of the KMS key for server-side encryption",
        visible_when=VisibleWhen(field="server_side_encryption_enabled", equals=True),
    )

    # ── Global Tables ─────────────────────────────────────────────────
    replica_regions: list[str] | None = TerraformField(
        None,
        group="Global Tables",
        description="List of regions for global table replicas",
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
