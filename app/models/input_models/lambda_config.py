"""Lambda-specific configuration model."""

from __future__ import annotations

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


class LambdaConfig(BaseServiceConfig):
    """Lambda-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.LAMBDA] = ServiceType.LAMBDA

    # Field order for schema output — all fields in logical group order.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        # General
        "function_name",
        "handler",
        "runtime",
        "description",
        # Performance
        "memory_size",
        "timeout",
        "ephemeral_storage_size",
        "reserved_concurrent_executions",
        "architectures",
        "snap_start_apply_on",
        # Deployment
        "package_type",
        "image_uri",
        "image_config",
        "publish",
        "layers",
        "s3_bucket",
        "s3_key",
        "s3_object_version",
        "source_code_hash",
        "filename",
        # VPC
        "vpc_subnet_ids",
        "vpc_security_group_ids",
        # Encryption
        "kms_key_arn",
        # Observability
        "tracing_mode",
        "logging_log_format",
        "logging_log_group",
        "logging_application_log_level",
        "logging_system_log_level",
        # Error Handling
        "dead_letter_target_arn",
        # Storage
        "file_system_arn",
        "file_system_local_mount_path",
        # Security
        "code_signing_config_arn",
        # Metadata
        "environment_variables",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    function_name: str = TerraformField(
        ...,
        group="General",
        description="Name of the Lambda function",
    )
    handler: str | None = TerraformField(
        "lambda_function.lambda_handler",
        group="General",
        description="Lambda function handler (module.function)",
    )
    runtime: str | None = TerraformField(
        "python3.14",
        group="General",
        description="Lambda function runtime",
        options=[
            OptionEntry(value="python3.14", label="Python 3.14", group="Python"),
            OptionEntry(value="python3.13", label="Python 3.13", group="Python"),
            OptionEntry(value="python3.12", label="Python 3.12", group="Python"),
            OptionEntry(value="python3.11", label="Python 3.11", group="Python"),
            OptionEntry(value="python3.10", label="Python 3.10", group="Python"),
            OptionEntry(value="nodejs24.x", label="Node.js 24.x", group="Node.js"),
            OptionEntry(value="nodejs22.x", label="Node.js 22.x", group="Node.js"),
            OptionEntry(value="java25", label="Java 25", group="Java"),
            OptionEntry(value="java21", label="Java 21", group="Java"),
            OptionEntry(value="java17", label="Java 17", group="Java"),
            OptionEntry(value="java11", label="Java 11", group="Java"),
            OptionEntry(value="java8.al2", label="Java 8 (AL2)", group="Java"),
            OptionEntry(value="dotnet10", label=".NET 10", group=".NET"),
            OptionEntry(value="dotnet9", label=".NET 9 (container only)", group=".NET"),
            OptionEntry(value="dotnet8", label=".NET 8", group=".NET"),
            OptionEntry(value="ruby4.0", label="Ruby 4.0", group="Ruby"),
            OptionEntry(value="ruby3.4", label="Ruby 3.4", group="Ruby"),
            OptionEntry(value="ruby3.3", label="Ruby 3.3", group="Ruby"),
            OptionEntry(
                value="provided.al2023",
                label="Custom Runtime (AL2023)",
                group="Custom",
            ),
            OptionEntry(
                value="provided.al2", label="Custom Runtime (AL2)", group="Custom"
            ),
        ],
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the Lambda function",
    )

    # ── Performance ───────────────────────────────────────────────────────
    memory_size: int | None = TerraformField(
        128,
        group="Performance",
        description="Amount of memory available to the function at runtime (MB)",
        validation=ValidationRule(min=128, max=10240),
    )
    timeout: int | None = TerraformField(
        3,
        group="Performance",
        description="Function execution timeout in seconds",
        validation=ValidationRule(min=1, max=900),
    )
    ephemeral_storage_size: int | None = TerraformField(
        512,
        group="Performance",
        description="Size of the function /tmp directory in MB",
        validation=ValidationRule(min=512, max=10240),
    )
    reserved_concurrent_executions: int | None = TerraformField(
        None,
        group="Performance",
        description="Number of reserved concurrent executions for this function",
        validation=ValidationRule(min=0, max=1000),
    )
    architectures: str | None = TerraformField(
        "x86_64",
        group="Performance",
        description="Instruction set architecture for the function",
        options=[
            OptionEntry(value="x86_64", label="x86_64"),
            OptionEntry(value="arm64", label="ARM64 (Graviton2)"),
        ],
    )
    snap_start_apply_on: str | None = TerraformField(
        None,
        group="Performance",
        description="SnapStart setting for the function",
        options=[
            OptionEntry(value="PublishedVersions", label="Published Versions"),
        ],
    )

    # ── Deployment ────────────────────────────────────────────────────────
    package_type: str | None = TerraformField(
        None,
        group="Deployment",
        description="Lambda deployment package type",
        options=[
            OptionEntry(value="Zip", label="Zip"),
            OptionEntry(value="Image", label="Container Image"),
        ],
    )
    image_uri: str | None = TerraformField(
        None,
        group="Deployment",
        description="ECR image URI for container-based Lambda",
        visible_when=VisibleWhen(field="package_type", equals="Image"),
    )
    image_config: dict | None = TerraformField(
        None,
        group="Deployment",
        description="Container image configuration overrides",
        tf_type="map",
        visible_when=VisibleWhen(field="package_type", equals="Image"),
    )
    publish: bool | None = TerraformField(
        False,
        group="Deployment",
        description="Whether to publish creation/change as a new Lambda function version",
    )
    layers: list[str] | None = TerraformField(
        None,
        group="Deployment",
        description="List of Lambda layer ARNs to attach to the function",
    )
    s3_bucket: str | None = TerraformField(
        None,
        group="Deployment",
        description="S3 bucket containing the function deployment package",
    )
    s3_key: str | None = TerraformField(
        None,
        group="Deployment",
        description="S3 object key of the function deployment package",
    )
    s3_object_version: str | None = TerraformField(
        None,
        group="Deployment",
        description="S3 object version of the function deployment package",
    )
    source_code_hash: str | None = TerraformField(
        None,
        group="Deployment",
        description="Base64-encoded SHA256 hash of the deployment package",
    )
    filename: str | None = TerraformField(
        None,
        group="Deployment",
        description="Path to the function deployment package within the local filesystem",
    )

    # ── VPC ───────────────────────────────────────────────────────────────
    vpc_subnet_ids: list[str] | None = TerraformField(
        None,
        group="VPC",
        description="List of subnet IDs for VPC configuration",
    )
    vpc_security_group_ids: list[str] | None = TerraformField(
        None,
        group="VPC",
        description="List of security group IDs for VPC configuration",
    )

    # ── Encryption ────────────────────────────────────────────────────────
    kms_key_arn: str | None = TerraformField(
        None,
        group="Encryption",
        description="KMS key ARN for environment variable encryption",
    )

    # ── Observability ─────────────────────────────────────────────────────
    tracing_mode: str | None = TerraformField(
        None,
        group="Observability",
        description="X-Ray tracing mode for the function",
        options=[
            OptionEntry(value="Active", label="Active"),
            OptionEntry(value="PassThrough", label="Pass Through"),
        ],
    )
    logging_log_format: str | None = TerraformField(
        None,
        group="Observability",
        description="Log format for the function (Text or JSON)",
        options=[
            OptionEntry(value="Text", label="Text"),
            OptionEntry(value="JSON", label="JSON"),
        ],
    )
    logging_log_group: str | None = TerraformField(
        None,
        group="Observability",
        description="CloudWatch log group for the function",
    )
    logging_application_log_level: str | None = TerraformField(
        None,
        group="Observability",
        description="Application log level for the function",
        options=[
            OptionEntry(value="TRACE", label="TRACE"),
            OptionEntry(value="DEBUG", label="DEBUG"),
            OptionEntry(value="INFO", label="INFO"),
            OptionEntry(value="WARN", label="WARN"),
            OptionEntry(value="ERROR", label="ERROR"),
            OptionEntry(value="FATAL", label="FATAL"),
        ],
    )
    logging_system_log_level: str | None = TerraformField(
        None,
        group="Observability",
        description="System log level for the function",
        options=[
            OptionEntry(value="DEBUG", label="DEBUG"),
            OptionEntry(value="INFO", label="INFO"),
            OptionEntry(value="WARN", label="WARN"),
        ],
    )

    # ── Error Handling ────────────────────────────────────────────────────
    dead_letter_target_arn: str | None = TerraformField(
        None,
        group="Error Handling",
        description="ARN of the dead letter queue (SQS or SNS) for failed invocations",
    )

    # ── Storage ───────────────────────────────────────────────────────────
    file_system_arn: str | None = TerraformField(
        None,
        group="Storage",
        description="ARN of the EFS access point for the function",
    )
    file_system_local_mount_path: str | None = TerraformField(
        None,
        group="Storage",
        description="Local mount path for the EFS file system (must start with /mnt/)",
        validation=ValidationRule(
            pattern="^/mnt/",
            pattern_description="Must start with /mnt/",
        ),
    )

    # ── Security ──────────────────────────────────────────────────────────
    code_signing_config_arn: str | None = TerraformField(
        None,
        group="Security",
        description="ARN of the code signing configuration for the function",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    environment_variables: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Environment variables for the Lambda function",
    )
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the Lambda function",
    )

    # ── Validators ────────────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_zip_requires_handler_runtime(self) -> "LambdaConfig":
        """handler and runtime are required when package_type is Zip or unset."""
        if self.package_type in (None, "Zip"):
            if not self.handler:
                raise ValueError(
                    "handler is required when package_type is 'Zip' or unset"
                )
            if not self.runtime:
                raise ValueError(
                    "runtime is required when package_type is 'Zip' or unset"
                )
        return self
