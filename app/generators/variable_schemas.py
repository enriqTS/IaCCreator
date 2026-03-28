"""Variable schemas per service type — defines which Terraform variables each service exposes."""

from pydantic import BaseModel

from app.models.input_models import ServiceType


class ValidationRule(BaseModel):
    """Validation constraints for a variable (min/max bounds, regex pattern, allowed values)."""

    min: int | float | None = None
    max: int | float | None = None
    pattern: str | None = None
    pattern_description: str | None = None
    allowed_values: list[str | int | float | bool] | None = None


class OptionEntry(BaseModel):
    """A predefined selectable option for a variable (value + human-readable label)."""

    value: str | int | float | bool
    label: str
    group: str | None = None


class VisibleWhen(BaseModel):
    """Conditional visibility rule — show this variable only when another field has a specific value."""

    field: str
    equals: str | int | float | bool


class VariableSchemaEntry(BaseModel):
    """Schema definition for a single Terraform variable exposed by a service."""

    name: str
    type: str  # "string" | "number" | "bool" | "map" | "list"
    description: str
    default: str | int | float | bool | None = None
    group: str = "General"
    options: list[OptionEntry] | None = None
    validation: ValidationRule | None = None
    visible_when: VisibleWhen | None = None

VARIABLE_SCHEMAS: dict[ServiceType, list[VariableSchemaEntry]] = {
    # ── Lambda (13 variables) ──────────────────────────────────────────
    ServiceType.LAMBDA: [
        # General
        VariableSchemaEntry(
            name="function_name",
            type="string",
            description="Name of the Lambda function",
            group="General",
        ),
        VariableSchemaEntry(
            name="handler",
            type="string",
            description="Lambda function handler (module.function)",
            default="lambda_function.lambda_handler",
            group="General",
        ),
        VariableSchemaEntry(
            name="runtime",
            type="string",
            description="Lambda function runtime",
            default="python3.12",
            group="General",
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
                OptionEntry(value="provided.al2023", label="Custom Runtime (AL2023)", group="Custom"),
                OptionEntry(value="provided.al2", label="Custom Runtime (AL2)", group="Custom"),
            ],
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the Lambda function",
            group="General",
        ),
        # Performance
        VariableSchemaEntry(
            name="memory_size",
            type="number",
            description="Amount of memory available to the function at runtime (MB)",
            default=128,
            group="Performance",
            validation=ValidationRule(min=128, max=10240),
        ),
        VariableSchemaEntry(
            name="timeout",
            type="number",
            description="Function execution timeout in seconds",
            default=3,
            group="Performance",
            validation=ValidationRule(min=1, max=900),
        ),
        VariableSchemaEntry(
            name="ephemeral_storage_size",
            type="number",
            description="Size of the function /tmp directory in MB",
            default=512,
            group="Performance",
            validation=ValidationRule(min=512, max=10240),
        ),
        VariableSchemaEntry(
            name="reserved_concurrent_executions",
            type="number",
            description="Number of reserved concurrent executions for this function",
            group="Performance",
            validation=ValidationRule(min=0, max=1000),
        ),
        VariableSchemaEntry(
            name="architectures",
            type="string",
            description="Instruction set architecture for the function",
            default="x86_64",
            group="Performance",
            options=[
                OptionEntry(value="x86_64", label="x86_64"),
                OptionEntry(value="arm64", label="ARM64 (Graviton2)"),
            ],
        ),
        # Deployment
        VariableSchemaEntry(
            name="publish",
            type="bool",
            description="Whether to publish creation/change as a new Lambda function version",
            default=False,
            group="Deployment",
        ),
        VariableSchemaEntry(
            name="layers",
            type="list",
            description="List of Lambda layer ARNs to attach to the function",
            group="Deployment",
        ),
        # Metadata
        VariableSchemaEntry(
            name="environment_variables",
            type="map",
            description="Environment variables for the Lambda function",
            group="Metadata",
        ),
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the Lambda function",
            group="Metadata",
        ),
    ],
    # ── S3 (6 variables) ──────────────────────────────────────────────
    ServiceType.S3: [
        # General
        VariableSchemaEntry(
            name="bucket_name",
            type="string",
            description="Name of the S3 bucket",
            group="General",
        ),
        VariableSchemaEntry(
            name="versioning",
            type="string",
            description="Versioning status for the S3 bucket",
            default="Enabled",
            group="General",
            options=[
                OptionEntry(value="Enabled", label="Enabled"),
                OptionEntry(value="Suspended", label="Suspended"),
                OptionEntry(value="Disabled", label="Disabled"),
            ],
        ),
        # Configuration
        VariableSchemaEntry(
            name="force_destroy",
            type="bool",
            description="Allow deletion of non-empty bucket by deleting all objects",
            default=False,
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="object_lock_enabled",
            type="bool",
            description="Enable S3 Object Lock on the bucket",
            default=False,
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="acceleration_status",
            type="string",
            description="Transfer acceleration status for the bucket",
            group="Configuration",
            options=[
                OptionEntry(value="Enabled", label="Enabled"),
                OptionEntry(value="Suspended", label="Suspended"),
            ],
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the S3 bucket",
            group="Metadata",
        ),
    ],
    # ── DynamoDB (12 variables) ────────────────────────────────────────
    ServiceType.DYNAMODB: [
        # General
        VariableSchemaEntry(
            name="table_name",
            type="string",
            description="Name of the DynamoDB table",
            group="General",
        ),
        VariableSchemaEntry(
            name="billing_mode",
            type="string",
            description="Billing mode for read/write throughput",
            default="PAY_PER_REQUEST",
            group="General",
            options=[
                OptionEntry(value="PAY_PER_REQUEST", label="On-Demand (PAY_PER_REQUEST)"),
                OptionEntry(value="PROVISIONED", label="Provisioned"),
            ],
        ),
        VariableSchemaEntry(
            name="table_class",
            type="string",
            description="Storage class for the DynamoDB table",
            default="STANDARD",
            group="General",
            options=[
                OptionEntry(value="STANDARD", label="Standard"),
                OptionEntry(value="STANDARD_INFREQUENT_ACCESS", label="Standard - Infrequent Access"),
            ],
        ),
        # Key Schema
        VariableSchemaEntry(
            name="hash_key",
            type="string",
            description="Attribute name for the partition (hash) key",
            group="Key Schema",
        ),
        VariableSchemaEntry(
            name="hash_key_type",
            type="string",
            description="Attribute type for the partition (hash) key",
            default="S",
            group="Key Schema",
            options=[
                OptionEntry(value="S", label="String"),
                OptionEntry(value="N", label="Number"),
                OptionEntry(value="B", label="Binary"),
            ],
        ),
        VariableSchemaEntry(
            name="range_key",
            type="string",
            description="Attribute name for the sort (range) key",
            group="Key Schema",
        ),
        VariableSchemaEntry(
            name="range_key_type",
            type="string",
            description="Attribute type for the sort (range) key",
            default="S",
            group="Key Schema",
            options=[
                OptionEntry(value="S", label="String"),
                OptionEntry(value="N", label="Number"),
                OptionEntry(value="B", label="Binary"),
            ],
        ),
        # Capacity
        VariableSchemaEntry(
            name="read_capacity",
            type="number",
            description="Provisioned read capacity units",
            default=5,
            group="Capacity",
            validation=ValidationRule(min=1, max=40000),
            visible_when=VisibleWhen(field="billing_mode", equals="PROVISIONED"),
        ),
        VariableSchemaEntry(
            name="write_capacity",
            type="number",
            description="Provisioned write capacity units",
            default=5,
            group="Capacity",
            validation=ValidationRule(min=1, max=40000),
            visible_when=VisibleWhen(field="billing_mode", equals="PROVISIONED"),
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the DynamoDB table",
            group="Metadata",
        ),
        VariableSchemaEntry(
            name="point_in_time_recovery_enabled",
            type="bool",
            description="Enable point-in-time recovery for the table",
            default=False,
            group="Metadata",
        ),
        VariableSchemaEntry(
            name="deletion_protection_enabled",
            type="bool",
            description="Enable deletion protection for the table",
            default=False,
            group="Metadata",
        ),
    ],
    # ── API Gateway (7 variables) ──────────────────────────────────────
    ServiceType.API_GATEWAY: [
        # General
        VariableSchemaEntry(
            name="api_name",
            type="string",
            description="Name of the API Gateway",
            group="General",
        ),
        VariableSchemaEntry(
            name="protocol_type",
            type="string",
            description="API protocol type",
            default="HTTP",
            group="General",
            options=[
                OptionEntry(value="HTTP", label="HTTP"),
                OptionEntry(value="WEBSOCKET", label="WebSocket"),
                OptionEntry(value="REST", label="REST"),
            ],
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the API",
            group="General",
        ),
        # Configuration
        VariableSchemaEntry(
            name="cors_configuration",
            type="map",
            description="CORS configuration for the API",
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="disable_execute_api_endpoint",
            type="bool",
            description="Disable the default execute-api endpoint",
            default=False,
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="route_selection_expression",
            type="string",
            description="Route selection expression for WebSocket APIs",
            group="Configuration",
            visible_when=VisibleWhen(field="protocol_type", equals="WEBSOCKET"),
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the API Gateway",
            group="Metadata",
        ),
    ],
    # ── CloudWatch (5 variables) ───────────────────────────────────────
    ServiceType.CLOUDWATCH: [
        # General
        VariableSchemaEntry(
            name="log_group_name",
            type="string",
            description="Name of the CloudWatch log group",
            group="General",
        ),
        VariableSchemaEntry(
            name="retention_in_days",
            type="number",
            description="Number of days to retain log events",
            default=30,
            group="General",
            options=[
                OptionEntry(value=0, label="Never expire"),
                OptionEntry(value=1, label="1 day"),
                OptionEntry(value=3, label="3 days"),
                OptionEntry(value=5, label="5 days"),
                OptionEntry(value=7, label="1 week"),
                OptionEntry(value=14, label="2 weeks"),
                OptionEntry(value=30, label="1 month"),
                OptionEntry(value=60, label="2 months"),
                OptionEntry(value=90, label="3 months"),
                OptionEntry(value=120, label="4 months"),
                OptionEntry(value=150, label="5 months"),
                OptionEntry(value=180, label="6 months"),
                OptionEntry(value=365, label="1 year"),
                OptionEntry(value=400, label="13 months"),
                OptionEntry(value=545, label="18 months"),
                OptionEntry(value=731, label="2 years"),
                OptionEntry(value=1096, label="3 years"),
                OptionEntry(value=1827, label="5 years"),
                OptionEntry(value=2192, label="6 years"),
                OptionEntry(value=2557, label="7 years"),
                OptionEntry(value=2922, label="8 years"),
                OptionEntry(value=3288, label="9 years"),
                OptionEntry(value=3653, label="10 years"),
            ],
            validation=ValidationRule(
                allowed_values=[0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
            ),
        ),
        # Configuration
        VariableSchemaEntry(
            name="kms_key_id",
            type="string",
            description="ARN of the KMS key to use for encrypting log data",
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="log_group_class",
            type="string",
            description="Log group class for the CloudWatch log group",
            default="STANDARD",
            group="Configuration",
            options=[
                OptionEntry(value="STANDARD", label="Standard"),
                OptionEntry(value="INFREQUENT_ACCESS", label="Infrequent Access"),
            ],
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the CloudWatch log group",
            group="Metadata",
        ),
    ],
}
