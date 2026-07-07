"""Lambda-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class LambdaConfig(BaseServiceConfig):
    """Lambda-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.LAMBDA] = ServiceType.LAMBDA

    # Field order must match VARIABLE_SCHEMAS[ServiceType.LAMBDA] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "function_name",
        "handler",
        "runtime",
        "description",
        "memory_size",
        "timeout",
        "ephemeral_storage_size",
        "reserved_concurrent_executions",
        "architectures",
        "publish",
        "layers",
        "environment_variables",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    function_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Lambda function",
    )
    handler: str | None = TerraformField(
        "lambda_function.lambda_handler",
        group="General",
        description="Lambda function handler (module.function)",
    )
    runtime: str | None = TerraformField(
        "python3.12",
        group="General",
        description="Lambda function runtime",
        options=[
            OptionEntry(value="python3.12", label="Python 3.12", group="Python"),
            OptionEntry(value="python3.11", label="Python 3.11", group="Python"),
            OptionEntry(value="python3.10", label="Python 3.10", group="Python"),
            OptionEntry(value="python3.9", label="Python 3.9", group="Python"),
            OptionEntry(value="nodejs20.x", label="Node.js 20.x", group="Node.js"),
            OptionEntry(value="nodejs18.x", label="Node.js 18.x", group="Node.js"),
            OptionEntry(value="java21", label="Java 21", group="Java"),
            OptionEntry(value="java17", label="Java 17", group="Java"),
            OptionEntry(value="java11", label="Java 11", group="Java"),
            OptionEntry(value="dotnet8", label=".NET 8", group=".NET"),
            OptionEntry(value="dotnet6", label=".NET 6", group=".NET"),
            OptionEntry(value="ruby3.3", label="Ruby 3.3", group="Ruby"),
            OptionEntry(value="ruby3.2", label="Ruby 3.2", group="Ruby"),
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

    # ── Deployment ────────────────────────────────────────────────────────
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

    # ── Internal (not Terraform variables) ────────────────────────────────
    is_layer: bool = False
