"""S3-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    VisibleWhen,
)


class S3Config(BaseServiceConfig):
    """S3-specific configuration."""

    service_type: Literal[ServiceType.S3] = ServiceType.S3

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        # General
        "bucket_name",
        "bucket_prefix",
        "versioning",
        "force_destroy",
        "object_lock_enabled",
        "acceleration_status",
        # Encryption
        "sse_algorithm",
        "sse_kms_key_id",
        "sse_bucket_key_enabled",
        # Lifecycle
        "lifecycle_rules",
        # CORS
        "cors_allowed_headers",
        "cors_allowed_methods",
        "cors_allowed_origins",
        "cors_expose_headers",
        "cors_max_age_seconds",
        # Logging
        "logging_target_bucket",
        "logging_target_prefix",
        # Website
        "website_index_document",
        "website_error_document",
        "website_redirect_all_requests_to",
        # Public Access
        "block_public_acls",
        "block_public_policy",
        "ignore_public_acls",
        "restrict_public_buckets",
        # Notifications
        "notification_lambda_arn",
        "notification_lambda_events",
        "notification_sqs_arn",
        "notification_sqs_events",
        "notification_sns_arn",
        "notification_sns_events",
        # Replication
        "replication_role_arn",
        "replication_destination_bucket",
        "replication_destination_storage_class",
        # Metadata
        "tags",
    )

    # ── General ──────────────────────────────────────────────────────────────
    bucket_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the S3 bucket",
    )
    bucket_prefix: str | None = TerraformField(
        None,
        group="General",
        description="Creates a unique bucket name beginning with the specified prefix",
    )
    versioning: str | None = TerraformField(
        "Enabled",
        group="General",
        description="Versioning status for the S3 bucket",
        options=[
            OptionEntry(value="Enabled", label="Enabled"),
            OptionEntry(value="Suspended", label="Suspended"),
            OptionEntry(value="Disabled", label="Disabled"),
        ],
    )

    # ── Configuration ────────────────────────────────────────────────────────
    force_destroy: bool | None = TerraformField(
        False,
        group="Configuration",
        description="Allow deletion of non-empty bucket by deleting all objects",
    )
    object_lock_enabled: bool | None = TerraformField(
        False,
        group="Configuration",
        description="Enable S3 Object Lock on the bucket",
    )
    acceleration_status: str | None = TerraformField(
        None,
        group="Configuration",
        description="Transfer acceleration status for the bucket",
        options=[
            OptionEntry(value="Enabled", label="Enabled"),
            OptionEntry(value="Suspended", label="Suspended"),
        ],
    )

    # ── Encryption ───────────────────────────────────────────────────────────
    sse_algorithm: str | None = TerraformField(
        None,
        group="Encryption",
        description="Server-side encryption algorithm to use",
        options=[
            OptionEntry(value="AES256", label="AES256"),
            OptionEntry(value="aws:kms", label="aws:kms"),
            OptionEntry(value="aws:kms:dsse", label="aws:kms:dsse"),
        ],
    )
    sse_kms_key_id: str | None = TerraformField(
        None,
        group="Encryption",
        description="ARN of the KMS key to use for server-side encryption",
        visible_when=VisibleWhen(field="sse_algorithm", equals="aws:kms"),
    )
    sse_bucket_key_enabled: bool | None = TerraformField(
        None,
        group="Encryption",
        description="Whether to enable S3 Bucket Key for SSE-KMS",
    )

    # ── Lifecycle ────────────────────────────────────────────────────────────
    lifecycle_rules: list[dict] | None = TerraformField(
        None,
        group="Lifecycle",
        description="Lifecycle rules for object management",
        tf_type="list",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_allowed_headers: list[str] | None = TerraformField(
        None,
        group="CORS",
        description="List of headers allowed in CORS requests",
    )
    cors_allowed_methods: list[str] | None = TerraformField(
        None,
        group="CORS",
        description="List of HTTP methods allowed in CORS requests",
        options=[
            OptionEntry(value="GET", label="GET"),
            OptionEntry(value="PUT", label="PUT"),
            OptionEntry(value="POST", label="POST"),
            OptionEntry(value="DELETE", label="DELETE"),
            OptionEntry(value="HEAD", label="HEAD"),
        ],
    )
    cors_allowed_origins: list[str] | None = TerraformField(
        None,
        group="CORS",
        description="List of origins allowed to make CORS requests",
    )
    cors_expose_headers: list[str] | None = TerraformField(
        None,
        group="CORS",
        description="List of headers exposed to the browser in CORS responses",
    )
    cors_max_age_seconds: int | None = TerraformField(
        None,
        group="CORS",
        description="Time in seconds the browser can cache the preflight response",
    )

    # ── Logging ──────────────────────────────────────────────────────────────
    logging_target_bucket: str | None = TerraformField(
        None,
        group="Logging",
        description="Name of the bucket to receive access logs",
    )
    logging_target_prefix: str | None = TerraformField(
        None,
        group="Logging",
        description="Prefix for access log object keys",
    )

    # ── Website ──────────────────────────────────────────────────────────────
    website_index_document: str | None = TerraformField(
        None,
        group="Website",
        description="Name of the index document for the website",
    )
    website_error_document: str | None = TerraformField(
        None,
        group="Website",
        description="Name of the error document for the website",
    )
    website_redirect_all_requests_to: str | None = TerraformField(
        None,
        group="Website",
        description="Hostname to redirect all website requests to",
    )

    # ── Public Access ────────────────────────────────────────────────────────
    block_public_acls: bool | None = TerraformField(
        True,
        group="Public Access",
        description="Whether to block public ACLs for the bucket",
    )
    block_public_policy: bool | None = TerraformField(
        True,
        group="Public Access",
        description="Whether to block public bucket policies",
    )
    ignore_public_acls: bool | None = TerraformField(
        True,
        group="Public Access",
        description="Whether to ignore public ACLs for the bucket",
    )
    restrict_public_buckets: bool | None = TerraformField(
        True,
        group="Public Access",
        description="Whether to restrict public bucket policies",
    )

    # ── Notifications ────────────────────────────────────────────────────────
    notification_lambda_arn: str | None = TerraformField(
        None,
        group="Notifications",
        description="ARN of the Lambda function for bucket notifications",
    )
    notification_lambda_events: list[str] | None = TerraformField(
        None,
        group="Notifications",
        description="S3 events that trigger the Lambda notification",
    )
    notification_sqs_arn: str | None = TerraformField(
        None,
        group="Notifications",
        description="ARN of the SQS queue for bucket notifications",
    )
    notification_sqs_events: list[str] | None = TerraformField(
        None,
        group="Notifications",
        description="S3 events that trigger the SQS notification",
    )
    notification_sns_arn: str | None = TerraformField(
        None,
        group="Notifications",
        description="ARN of the SNS topic for bucket notifications",
    )
    notification_sns_events: list[str] | None = TerraformField(
        None,
        group="Notifications",
        description="S3 events that trigger the SNS notification",
    )

    # ── Replication ──────────────────────────────────────────────────────────
    replication_role_arn: str | None = TerraformField(
        None,
        group="Replication",
        description="ARN of the IAM role for S3 replication",
    )
    replication_destination_bucket: str | None = TerraformField(
        None,
        group="Replication",
        description="ARN of the destination bucket for replication",
    )
    replication_destination_storage_class: str | None = TerraformField(
        None,
        group="Replication",
        description="Storage class for replicated objects in the destination bucket",
        options=[
            OptionEntry(value="STANDARD", label="Standard"),
            OptionEntry(value="REDUCED_REDUNDANCY", label="Reduced Redundancy"),
            OptionEntry(value="STANDARD_IA", label="Standard-IA"),
            OptionEntry(value="ONEZONE_IA", label="One Zone-IA"),
            OptionEntry(value="INTELLIGENT_TIERING", label="Intelligent-Tiering"),
            OptionEntry(value="GLACIER", label="Glacier Flexible Retrieval"),
            OptionEntry(value="GLACIER_IR", label="Glacier Instant Retrieval"),
            OptionEntry(value="DEEP_ARCHIVE", label="Glacier Deep Archive"),
        ],
    )

    # ── Metadata ─────────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the S3 bucket",
        tf_type="map",
    )
