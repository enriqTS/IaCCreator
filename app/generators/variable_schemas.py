"""Variable schemas per service type — defines which Terraform variables each service exposes.

NOTE: The model classes (ValidationRule, OptionEntry, VisibleWhen, VariableSchemaEntry)
are now canonical in app.models.input_models._metadata. This module re-exports them for
backward compatibility with schema_validator.py and tfvars_generator.py until those are
migrated (tasks 12.4/12.5).

VARIABLE_SCHEMAS is retained here as the legacy static dictionary. Once schema_validator
and tfvars_generator are updated to use model introspection, this file can be deleted entirely.
"""

from app.models.input_models._metadata import (
    OptionEntry,
    ValidationRule,
    VariableSchemaEntry,
    VisibleWhen,
)
from app.models.input_models import ServiceType

# Re-export model classes for backward compatibility
__all__ = [
    "OptionEntry",
    "ValidationRule",
    "VariableSchemaEntry",
    "VisibleWhen",
    "VARIABLE_SCHEMAS",
]

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
                OptionEntry(
                    value="provided.al2023",
                    label="Custom Runtime (AL2023)",
                    group="Custom",
                ),
                OptionEntry(
                    value="provided.al2", label="Custom Runtime (AL2)", group="Custom"
                ),
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
                OptionEntry(
                    value="PAY_PER_REQUEST", label="On-Demand (PAY_PER_REQUEST)"
                ),
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
                OptionEntry(
                    value="STANDARD_INFREQUENT_ACCESS",
                    label="Standard - Infrequent Access",
                ),
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
    # ── API Gateway (~35 variables) ───────────────────────────────────
    ServiceType.API_GATEWAY: [
        # ─── General ───────────────────────────────────────────────────
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
        # ─── Routes ───────────────────────────────────────────────────
        VariableSchemaEntry(
            name="route_method",
            type="string",
            description="HTTP method for the route",
            default="ANY",
            group="Routes",
            options=[
                OptionEntry(value="GET", label="GET"),
                OptionEntry(value="POST", label="POST"),
                OptionEntry(value="PUT", label="PUT"),
                OptionEntry(value="DELETE", label="DELETE"),
                OptionEntry(value="PATCH", label="PATCH"),
                OptionEntry(value="HEAD", label="HEAD"),
                OptionEntry(value="OPTIONS", label="OPTIONS"),
                OptionEntry(value="ANY", label="ANY"),
            ],
        ),
        VariableSchemaEntry(
            name="route_path",
            type="string",
            description="Route path (e.g., /users/{id})",
            group="Routes",
        ),
        VariableSchemaEntry(
            name="route_selection_expression",
            type="string",
            description="Route selection expression for WebSocket APIs",
            group="Routes",
            visible_when=VisibleWhen(field="protocol_type", equals="WEBSOCKET"),
        ),
        # ─── Stages ───────────────────────────────────────────────────
        VariableSchemaEntry(
            name="stage_name",
            type="string",
            description="Name of the deployment stage (e.g., $default, dev, prod)",
            group="Stages",
        ),
        VariableSchemaEntry(
            name="auto_deploy",
            type="bool",
            description="Whether to auto-deploy changes to this stage",
            default=True,
            group="Stages",
        ),
        VariableSchemaEntry(
            name="stage_variables",
            type="map",
            description="Stage variables as key-value pairs (max 50 entries)",
            group="Stages",
        ),
        # ─── Authorizers ──────────────────────────────────────────────
        VariableSchemaEntry(
            name="authorizer_type",
            type="string",
            description="Type of authorizer to attach to the API",
            group="Authorizers",
            options=[
                OptionEntry(value="JWT", label="JWT"),
                OptionEntry(value="REQUEST", label="Lambda (REQUEST)"),
                OptionEntry(value="COGNITO_USER_POOLS", label="Cognito User Pools"),
            ],
        ),
        VariableSchemaEntry(
            name="jwt_issuer",
            type="string",
            description="Issuer URL for the JWT authorizer",
            group="Authorizers",
            visible_when=VisibleWhen(field="authorizer_type", equals="JWT"),
        ),
        VariableSchemaEntry(
            name="jwt_audience",
            type="string",
            description="Audience value(s) for the JWT authorizer",
            group="Authorizers",
            visible_when=VisibleWhen(field="authorizer_type", equals="JWT"),
        ),
        VariableSchemaEntry(
            name="lambda_authorizer_uri",
            type="string",
            description="Lambda function invoke ARN for the REQUEST authorizer",
            group="Authorizers",
            visible_when=VisibleWhen(field="authorizer_type", equals="REQUEST"),
        ),
        VariableSchemaEntry(
            name="authorizer_payload_format_version",
            type="string",
            description="Payload format version for the Lambda authorizer",
            group="Authorizers",
            visible_when=VisibleWhen(field="authorizer_type", equals="REQUEST"),
            options=[
                OptionEntry(value="1.0", label="1.0"),
                OptionEntry(value="2.0", label="2.0"),
            ],
        ),
        VariableSchemaEntry(
            name="cognito_user_pool_endpoint",
            type="string",
            description="Cognito User Pool endpoint URL",
            group="Authorizers",
            visible_when=VisibleWhen(
                field="authorizer_type", equals="COGNITO_USER_POOLS"
            ),
        ),
        VariableSchemaEntry(
            name="cognito_client_ids",
            type="list",
            description="List of Cognito User Pool client IDs",
            group="Authorizers",
            visible_when=VisibleWhen(
                field="authorizer_type", equals="COGNITO_USER_POOLS"
            ),
        ),
        # ─── Custom Domain ────────────────────────────────────────────
        VariableSchemaEntry(
            name="custom_domain_name",
            type="string",
            description="Custom domain name for the API (e.g., api.example.com)",
            group="Custom Domain",
        ),
        VariableSchemaEntry(
            name="certificate_arn",
            type="string",
            description="ARN of the ACM certificate for the custom domain",
            group="Custom Domain",
        ),
        # ─── Integrations ─────────────────────────────────────────────
        VariableSchemaEntry(
            name="integration_type",
            type="string",
            description="Type of backend integration",
            group="Integrations",
            options=[
                OptionEntry(value="AWS_PROXY", label="AWS Lambda (AWS_PROXY)"),
                OptionEntry(value="HTTP_PROXY", label="HTTP Proxy (HTTP_PROXY)"),
                OptionEntry(value="HTTP", label="HTTP Custom (HTTP)"),
            ],
        ),
        VariableSchemaEntry(
            name="integration_uri",
            type="string",
            description="URI of the integration target",
            group="Integrations",
        ),
        VariableSchemaEntry(
            name="integration_method",
            type="string",
            description="HTTP method for the integration (required for HTTP_PROXY and HTTP)",
            group="Integrations",
            visible_when=VisibleWhen(field="integration_type", equals="HTTP_PROXY"),
        ),
        # ─── Rate Limiting ────────────────────────────────────────────
        VariableSchemaEntry(
            name="throttling_burst_limit",
            type="number",
            description="Maximum number of concurrent requests (burst)",
            group="Rate Limiting",
            validation=ValidationRule(min=1, max=5000),
        ),
        VariableSchemaEntry(
            name="throttling_rate_limit",
            type="number",
            description="Maximum number of requests per second (steady-state)",
            group="Rate Limiting",
            validation=ValidationRule(min=1.0, max=10000.0),
        ),
        # ─── VPC Link ─────────────────────────────────────────────────
        VariableSchemaEntry(
            name="vpc_link_name",
            type="string",
            description="Name of the VPC link for private integrations",
            group="VPC Link",
        ),
        VariableSchemaEntry(
            name="vpc_link_subnet_ids",
            type="list",
            description="List of subnet IDs for the VPC link (1-3 entries)",
            group="VPC Link",
        ),
        VariableSchemaEntry(
            name="vpc_link_security_group_ids",
            type="list",
            description="List of security group IDs for the VPC link (1-5 entries)",
            group="VPC Link",
        ),
        # ─── Metadata ─────────────────────────────────────────────────
        VariableSchemaEntry(
            name="cors_configuration",
            type="map",
            description="CORS configuration for the API",
            group="Metadata",
        ),
        VariableSchemaEntry(
            name="disable_execute_api_endpoint",
            type="bool",
            description="Disable the default execute-api endpoint",
            default=False,
            group="Metadata",
        ),
        VariableSchemaEntry(
            name="api_key_required",
            type="bool",
            description="Whether API key is required for routes",
            default=False,
            group="Metadata",
        ),
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
                allowed_values=[
                    0,
                    1,
                    3,
                    5,
                    7,
                    14,
                    30,
                    60,
                    90,
                    120,
                    150,
                    180,
                    365,
                    400,
                    545,
                    731,
                    1096,
                    1827,
                    2192,
                    2557,
                    2922,
                    3288,
                    3653,
                ],
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
    # ── EC2 (3 variables) ─────────────────────────────────────────────
    ServiceType.EC2: [
        VariableSchemaEntry(
            name="instance_name",
            type="string",
            description="Name tag for the EC2 instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="ami",
            type="string",
            description="AMI ID for the instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="instance_type",
            type="string",
            description="EC2 instance type",
            default="t3.micro",
            group="General",
        ),
    ],
    # ── ECS (4 variables) ─────────────────────────────────────────────
    ServiceType.ECS: [
        VariableSchemaEntry(
            name="cluster_name",
            type="string",
            description="Name of the ECS cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="task_family",
            type="string",
            description="Family name for the ECS task definition",
            group="General",
        ),
        VariableSchemaEntry(
            name="ecs_cpu",
            type="string",
            description="CPU units for the ECS task",
            default="256",
            group="Performance",
        ),
        VariableSchemaEntry(
            name="ecs_memory",
            type="string",
            description="Memory (MiB) for the ECS task",
            default="512",
            group="Performance",
        ),
    ],
    # ── EKS (3 variables) ─────────────────────────────────────────────
    ServiceType.EKS: [
        VariableSchemaEntry(
            name="cluster_name",
            type="string",
            description="Name of the EKS cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="cluster_role_arn",
            type="string",
            description="ARN of the IAM role for the EKS cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="subnet_ids",
            type="list",
            description="List of subnet IDs for the EKS cluster VPC config",
            group="Networking",
        ),
    ],
    # ── Elastic Beanstalk (2 variables) ───────────────────────────────
    ServiceType.ELASTIC_BEANSTALK: [
        VariableSchemaEntry(
            name="application_name",
            type="string",
            description="Name of the Elastic Beanstalk application",
            group="General",
        ),
        VariableSchemaEntry(
            name="environment_name",
            type="string",
            description="Name of the Elastic Beanstalk environment",
            group="General",
        ),
    ],
    # ── App Runner (2 variables) ──────────────────────────────────────
    ServiceType.APP_RUNNER: [
        VariableSchemaEntry(
            name="service_name",
            type="string",
            description="Name of the App Runner service",
            group="General",
        ),
        VariableSchemaEntry(
            name="image_identifier",
            type="string",
            description="Container image identifier for the App Runner service",
            group="General",
        ),
    ],
    # ── Batch (2 variables) ───────────────────────────────────────────
    ServiceType.BATCH: [
        VariableSchemaEntry(
            name="compute_environment_name",
            type="string",
            description="Name of the Batch compute environment",
            group="General",
        ),
        VariableSchemaEntry(
            name="service_role_arn",
            type="string",
            description="ARN of the IAM service role for Batch",
            group="General",
        ),
    ],
    # ── EC2 Image Builder (3 variables) ───────────────────────────────
    ServiceType.EC2_IMAGE_BUILDER: [
        VariableSchemaEntry(
            name="pipeline_name",
            type="string",
            description="Name of the Image Builder pipeline",
            group="General",
        ),
        VariableSchemaEntry(
            name="image_recipe_arn",
            type="string",
            description="ARN of the image recipe",
            group="General",
        ),
        VariableSchemaEntry(
            name="infrastructure_configuration_arn",
            type="string",
            description="ARN of the infrastructure configuration",
            group="General",
        ),
    ],
    # ── Lightsail (4 variables) ───────────────────────────────────────
    ServiceType.LIGHTSAIL: [
        VariableSchemaEntry(
            name="instance_name",
            type="string",
            description="Name of the Lightsail instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="blueprint_id",
            type="string",
            description="Blueprint ID for the Lightsail instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="bundle_id",
            type="string",
            description="Bundle ID for the Lightsail instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="availability_zone",
            type="string",
            description="Availability zone for the Lightsail instance",
            group="General",
        ),
    ],
    # ── ECR (1 variable) ──────────────────────────────────────────────
    ServiceType.ECR: [
        VariableSchemaEntry(
            name="repository_name",
            type="string",
            description="Name of the ECR repository",
            group="General",
        ),
    ],
    # ── Athena (1 variable) ───────────────────────────────────────────
    ServiceType.ATHENA: [
        VariableSchemaEntry(
            name="workgroup_name",
            type="string",
            description="Name of the Athena workgroup",
            group="General",
        ),
    ],
    # ── CloudSearch (1 variable) ──────────────────────────────────────
    ServiceType.CLOUDSEARCH: [
        VariableSchemaEntry(
            name="domain_name",
            type="string",
            description="Name of the CloudSearch domain",
            group="General",
        ),
    ],
    # ── EMR (3 variables) ─────────────────────────────────────────────
    ServiceType.EMR: [
        VariableSchemaEntry(
            name="cluster_name",
            type="string",
            description="Name of the EMR cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="release_label",
            type="string",
            description="EMR release label",
            group="General",
        ),
        VariableSchemaEntry(
            name="service_role",
            type="string",
            description="IAM service role for the EMR cluster",
            group="General",
        ),
    ],
    # ── Glue (1 variable) ─────────────────────────────────────────────
    ServiceType.GLUE: [
        VariableSchemaEntry(
            name="database_name",
            type="string",
            description="Name of the Glue catalog database",
            group="General",
        ),
    ],
    # ── Kinesis (2 variables) ─────────────────────────────────────────
    ServiceType.KINESIS: [
        VariableSchemaEntry(
            name="stream_name",
            type="string",
            description="Name of the Kinesis stream",
            group="General",
        ),
        VariableSchemaEntry(
            name="shard_count",
            type="number",
            description="Number of shards for the Kinesis stream",
            group="General",
        ),
    ],
    # ── Kinesis Firehose (2 variables) ────────────────────────────────
    ServiceType.KINESIS_FIREHOSE: [
        VariableSchemaEntry(
            name="stream_name",
            type="string",
            description="Name of the Firehose delivery stream",
            group="General",
        ),
        VariableSchemaEntry(
            name="destination",
            type="string",
            description="Destination for the Firehose delivery stream",
            group="General",
        ),
    ],
    # ── MSK (3 variables) ─────────────────────────────────────────────
    ServiceType.MSK: [
        VariableSchemaEntry(
            name="cluster_name",
            type="string",
            description="Name of the MSK cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="kafka_version",
            type="string",
            description="Apache Kafka version for the MSK cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="number_of_broker_nodes",
            type="number",
            description="Number of broker nodes in the MSK cluster",
            group="General",
        ),
    ],
    # ── OpenSearch (1 variable) ───────────────────────────────────────
    ServiceType.OPENSEARCH: [
        VariableSchemaEntry(
            name="domain_name",
            type="string",
            description="Name of the OpenSearch domain",
            group="General",
        ),
    ],
    # ── Redshift (3 variables) ────────────────────────────────────────
    ServiceType.REDSHIFT: [
        VariableSchemaEntry(
            name="cluster_identifier",
            type="string",
            description="Identifier for the Redshift cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="node_type",
            type="string",
            description="Node type for the Redshift cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="master_username",
            type="string",
            description="Master username for the Redshift cluster",
            group="General",
        ),
    ],
    # ── Connect (3 variables) ─────────────────────────────────────────
    ServiceType.CONNECT: [
        VariableSchemaEntry(
            name="identity_management_type",
            type="string",
            description="Identity management type for the Connect instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="inbound_calls_enabled",
            type="bool",
            description="Whether inbound calls are enabled",
            group="General",
        ),
        VariableSchemaEntry(
            name="outbound_calls_enabled",
            type="bool",
            description="Whether outbound calls are enabled",
            group="General",
        ),
    ],
    # ── SES (1 variable) ──────────────────────────────────────────────
    ServiceType.SES: [
        VariableSchemaEntry(
            name="domain",
            type="string",
            description="Domain name for SES identity",
            group="General",
        ),
    ],
    # ── Pinpoint (1 variable) ─────────────────────────────────────────
    ServiceType.PINPOINT: [
        VariableSchemaEntry(
            name="app_name",
            type="string",
            description="Name of the Pinpoint application",
            group="General",
        ),
    ],
    # ── Aurora (3 variables) ──────────────────────────────────────────
    ServiceType.AURORA: [
        VariableSchemaEntry(
            name="cluster_identifier",
            type="string",
            description="Identifier for the Aurora cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="engine",
            type="string",
            description="Database engine for the Aurora cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="master_username",
            type="string",
            description="Master username for the Aurora cluster",
            group="General",
        ),
    ],
    # ── DocumentDB (2 variables) ──────────────────────────────────────
    ServiceType.DOCUMENTDB: [
        VariableSchemaEntry(
            name="cluster_identifier",
            type="string",
            description="Identifier for the DocumentDB cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="master_username",
            type="string",
            description="Master username for the DocumentDB cluster",
            group="General",
        ),
    ],
    # ── ElastiCache (4 variables) ─────────────────────────────────────
    ServiceType.ELASTICACHE: [
        VariableSchemaEntry(
            name="cluster_id",
            type="string",
            description="Identifier for the ElastiCache cluster",
            group="General",
        ),
        VariableSchemaEntry(
            name="engine",
            type="string",
            description="Cache engine type",
            group="General",
        ),
        VariableSchemaEntry(
            name="node_type",
            type="string",
            description="ElastiCache node type",
            group="General",
        ),
        VariableSchemaEntry(
            name="num_cache_nodes",
            type="number",
            description="Number of cache nodes in the cluster",
            group="General",
        ),
    ],
    # ── Neptune (1 variable) ──────────────────────────────────────────
    ServiceType.NEPTUNE: [
        VariableSchemaEntry(
            name="cluster_identifier",
            type="string",
            description="Identifier for the Neptune cluster",
            group="General",
        ),
    ],
    # ── RDS (5 variables) ─────────────────────────────────────────────
    ServiceType.RDS: [
        VariableSchemaEntry(
            name="db_identifier",
            type="string",
            description="Identifier for the RDS instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="engine",
            type="string",
            description="Database engine type",
            group="General",
        ),
        VariableSchemaEntry(
            name="instance_class",
            type="string",
            description="RDS instance class",
            default="db.t3.micro",
            group="General",
        ),
        VariableSchemaEntry(
            name="allocated_storage",
            type="number",
            description="Allocated storage in GB",
            default=20,
            group="General",
        ),
        VariableSchemaEntry(
            name="username",
            type="string",
            description="Master username for the database",
            group="General",
        ),
    ],
    # ── Timestream (1 variable) ───────────────────────────────────────
    ServiceType.TIMESTREAM: [
        VariableSchemaEntry(
            name="database_name",
            type="string",
            description="Name of the Timestream database",
            group="General",
        ),
    ],
    # ── CodeBuild (3 variables) ───────────────────────────────────────
    ServiceType.CODEBUILD: [
        VariableSchemaEntry(
            name="project_name",
            type="string",
            description="Name of the CodeBuild project",
            group="General",
        ),
        VariableSchemaEntry(
            name="service_role",
            type="string",
            description="IAM service role ARN for CodeBuild",
            group="General",
        ),
        VariableSchemaEntry(
            name="source_type",
            type="string",
            description="Source type for the CodeBuild project",
            group="General",
        ),
    ],
    # ── CodeCommit (1 variable) ───────────────────────────────────────
    ServiceType.CODECOMMIT: [
        VariableSchemaEntry(
            name="repository_name",
            type="string",
            description="Name of the CodeCommit repository",
            group="General",
        ),
    ],
    # ── CodeDeploy (2 variables) ──────────────────────────────────────
    ServiceType.CODEDEPLOY: [
        VariableSchemaEntry(
            name="app_name",
            type="string",
            description="Name of the CodeDeploy application",
            group="General",
        ),
        VariableSchemaEntry(
            name="compute_platform",
            type="string",
            description="Compute platform for CodeDeploy",
            group="General",
        ),
    ],
    # ── CodePipeline (2 variables) ────────────────────────────────────
    ServiceType.CODEPIPELINE: [
        VariableSchemaEntry(
            name="pipeline_name",
            type="string",
            description="Name of the CodePipeline pipeline",
            group="General",
        ),
        VariableSchemaEntry(
            name="role_arn",
            type="string",
            description="IAM role ARN for CodePipeline",
            group="General",
        ),
    ],
    # ── AppStream (2 variables) ───────────────────────────────────────
    ServiceType.APPSTREAM: [
        VariableSchemaEntry(
            name="fleet_name",
            type="string",
            description="Name of the AppStream fleet",
            group="General",
        ),
        VariableSchemaEntry(
            name="instance_type",
            type="string",
            description="Instance type for the AppStream fleet",
            group="General",
        ),
    ],
    # ── Amplify (1 variable) ──────────────────────────────────────────
    ServiceType.AMPLIFY: [
        VariableSchemaEntry(
            name="app_name",
            type="string",
            description="Name of the Amplify application",
            group="General",
        ),
    ],
    # ── GameLift (2 variables) ────────────────────────────────────────
    ServiceType.GAMELIFT: [
        VariableSchemaEntry(
            name="fleet_name",
            type="string",
            description="Name of the GameLift fleet",
            group="General",
        ),
        VariableSchemaEntry(
            name="ec2_instance_type",
            type="string",
            description="EC2 instance type for the GameLift fleet",
            group="General",
        ),
    ],
    # ── Machine Learning ───────────────────────────────────────────────
    # ── Bedrock (7 variables, 3 groups) ────────────────────────────────
    ServiceType.BEDROCK: [
        # General
        VariableSchemaEntry(
            name="model_name",
            type="string",
            description="Name of the custom model",
            group="General",
        ),
        VariableSchemaEntry(
            name="base_model_identifier",
            type="string",
            description="Base model identifier for customization",
            group="General",
            options=[
                OptionEntry(
                    value="amazon.titan-text-express-v1",
                    label="Amazon Titan Text Express",
                ),
                OptionEntry(
                    value="amazon.titan-embed-text-v1", label="Amazon Titan Embed Text"
                ),
                OptionEntry(value="anthropic.claude-v2", label="Anthropic Claude v2"),
                OptionEntry(
                    value="meta.llama2-13b-chat-v1", label="Meta Llama 2 13B Chat"
                ),
            ],
        ),
        VariableSchemaEntry(
            name="role_arn",
            type="string",
            description="IAM role ARN for Bedrock",
            group="General",
        ),
        # Training
        VariableSchemaEntry(
            name="training_data_s3_uri",
            type="string",
            description="S3 URI of the training data",
            group="Training",
            validation=ValidationRule(
                pattern="^s3://",
                pattern_description="Must be an S3 URI starting with s3://",
            ),
        ),
        VariableSchemaEntry(
            name="output_data_s3_uri",
            type="string",
            description="S3 URI for the output data",
            group="Training",
            validation=ValidationRule(
                pattern="^s3://",
                pattern_description="Must be an S3 URI starting with s3://",
            ),
        ),
        VariableSchemaEntry(
            name="hyperparameters",
            type="map",
            description="Key-value pairs for training hyperparameters such as epoch count, batch size, and learning rate",
            group="Training",
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="String key-value pairs for resource tagging",
            group="Metadata",
        ),
    ],
    # ── SageMaker (7 variables, 3 groups) ──────────────────────────────
    ServiceType.SAGEMAKER: [
        # General
        VariableSchemaEntry(
            name="notebook_instance_name",
            type="string",
            description="Name of the SageMaker notebook instance",
            group="General",
        ),
        VariableSchemaEntry(
            name="instance_type",
            type="string",
            description="Instance type for the notebook instance",
            group="General",
            options=[
                OptionEntry(value="ml.t3.medium", label="ml.t3.medium"),
                OptionEntry(value="ml.t3.large", label="ml.t3.large"),
                OptionEntry(value="ml.m5.large", label="ml.m5.large"),
                OptionEntry(value="ml.m5.xlarge", label="ml.m5.xlarge"),
                OptionEntry(value="ml.c5.large", label="ml.c5.large"),
                OptionEntry(value="ml.c5.xlarge", label="ml.c5.xlarge"),
            ],
        ),
        VariableSchemaEntry(
            name="role_arn",
            type="string",
            description="IAM role ARN for the notebook instance",
            group="General",
        ),
        # Configuration
        VariableSchemaEntry(
            name="volume_size",
            type="number",
            description="Volume size for the notebook instance in GB",
            default=5,
            group="Configuration",
            validation=ValidationRule(min=5, max=16384),
        ),
        VariableSchemaEntry(
            name="direct_internet_access",
            type="bool",
            description="Whether direct internet access is enabled for the notebook instance",
            default=True,
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="root_access",
            type="bool",
            description="Whether root access is enabled for the notebook instance",
            default=True,
            group="Configuration",
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the SageMaker notebook instance",
            group="Metadata",
        ),
    ],
    # ── Amazon Q (5 variables, 2 groups) ───────────────────────────────
    ServiceType.AMAZON_Q: [
        # General
        VariableSchemaEntry(
            name="application_name",
            type="string",
            description="Name of the Amazon Q application",
            group="General",
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the Amazon Q application",
            group="General",
        ),
        VariableSchemaEntry(
            name="identity_type",
            type="string",
            description="Identity provider type for the Amazon Q application",
            group="General",
            options=[
                OptionEntry(value="AWS_IAM_IDP", label="AWS IAM Identity Provider"),
                OptionEntry(value="AWS_IAM_IC", label="AWS IAM Identity Center"),
                OptionEntry(value="AWS_QUICKSIGHT", label="Amazon QuickSight"),
            ],
        ),
        VariableSchemaEntry(
            name="role_arn",
            type="string",
            description="IAM role ARN for the Amazon Q application",
            group="General",
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the Amazon Q application",
            group="Metadata",
        ),
    ],
    # ── Bedrock Agent (8 variables, 3 groups) ──────────────────────────
    ServiceType.BEDROCK_AGENT: [
        # General
        VariableSchemaEntry(
            name="agent_name",
            type="string",
            description="Name of the Bedrock Agent",
            group="General",
        ),
        VariableSchemaEntry(
            name="foundation_model",
            type="string",
            description="Foundation model identifier for the agent",
            group="General",
            options=[
                OptionEntry(value="anthropic.claude-v2", label="Anthropic Claude v2"),
                OptionEntry(
                    value="anthropic.claude-3-sonnet-20240229-v1:0",
                    label="Anthropic Claude 3 Sonnet",
                ),
                OptionEntry(
                    value="anthropic.claude-3-haiku-20240307-v1:0",
                    label="Anthropic Claude 3 Haiku",
                ),
                OptionEntry(
                    value="amazon.titan-text-express-v1",
                    label="Amazon Titan Text Express",
                ),
                OptionEntry(
                    value="meta.llama3-8b-instruct-v1:0",
                    label="Meta Llama 3 8B Instruct",
                ),
            ],
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the Bedrock Agent",
            group="General",
        ),
        VariableSchemaEntry(
            name="instruction",
            type="string",
            description="Instruction for the Bedrock Agent",
            group="General",
        ),
        VariableSchemaEntry(
            name="agent_resource_role_arn",
            type="string",
            description="IAM role ARN for the Bedrock Agent",
            group="General",
        ),
        # Configuration
        VariableSchemaEntry(
            name="idle_session_ttl_in_seconds",
            type="number",
            description="Idle session timeout in seconds",
            default=600,
            group="Configuration",
            validation=ValidationRule(min=60, max=3600),
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the Bedrock Agent",
            group="Metadata",
        ),
    ],
    # ── Bedrock Knowledge Base (9 variables, 3 groups) ─────────────────
    ServiceType.BEDROCK_KNOWLEDGE_BASE: [
        # General
        VariableSchemaEntry(
            name="knowledge_base_name",
            type="string",
            description="Name of the knowledge base",
            group="General",
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the knowledge base",
            group="General",
        ),
        VariableSchemaEntry(
            name="role_arn",
            type="string",
            description="IAM role ARN for the knowledge base",
            group="General",
        ),
        VariableSchemaEntry(
            name="embedding_model_arn",
            type="string",
            description="ARN of the embedding model for vector indexing",
            group="General",
            options=[
                OptionEntry(
                    value="amazon.titan-embed-text-v1",
                    label="Titan Embeddings G1 - Text",
                ),
                OptionEntry(
                    value="amazon.titan-embed-text-v2:0",
                    label="Titan Embeddings G1 - Text v2",
                ),
                OptionEntry(
                    value="cohere.embed-english-v3", label="Cohere Embed English v3"
                ),
            ],
        ),
        # Storage Configuration
        VariableSchemaEntry(
            name="storage_type",
            type="string",
            description="Vector storage type for the knowledge base",
            default="OPENSEARCH_SERVERLESS",
            group="Storage Configuration",
            options=[
                OptionEntry(
                    value="OPENSEARCH_SERVERLESS", label="OpenSearch Serverless"
                ),
                OptionEntry(value="PINECONE", label="Pinecone"),
                OptionEntry(value="RDS", label="RDS Aurora PostgreSQL"),
            ],
        ),
        VariableSchemaEntry(
            name="vector_field",
            type="string",
            description="Name of the vector field in the storage",
            group="Storage Configuration",
        ),
        VariableSchemaEntry(
            name="text_field",
            type="string",
            description="Name of the text field in the storage",
            group="Storage Configuration",
        ),
        VariableSchemaEntry(
            name="metadata_field",
            type="string",
            description="Name of the metadata field in the storage",
            group="Storage Configuration",
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the Bedrock Knowledge Base",
            group="Metadata",
        ),
    ],
    # ── Bedrock Guardrail (6 variables, 3 groups) ──────────────────────
    ServiceType.BEDROCK_GUARDRAIL: [
        # General
        VariableSchemaEntry(
            name="guardrail_name",
            type="string",
            description="Name of the Bedrock Guardrail",
            group="General",
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the guardrail",
            group="General",
        ),
        VariableSchemaEntry(
            name="blocked_input_messaging",
            type="string",
            description="Message to return when input is blocked",
            group="General",
        ),
        VariableSchemaEntry(
            name="blocked_outputs_messaging",
            type="string",
            description="Message to return when output is blocked",
            group="General",
        ),
        # Content Policy
        VariableSchemaEntry(
            name="content_policy_strength",
            type="string",
            description="Content filtering strength level",
            default="MEDIUM",
            group="Content Policy",
            options=[
                OptionEntry(value="NONE", label="None"),
                OptionEntry(value="LOW", label="Low"),
                OptionEntry(value="MEDIUM", label="Medium"),
                OptionEntry(value="HIGH", label="High"),
            ],
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the Bedrock Guardrail",
            group="Metadata",
        ),
    ],
    # ── Bedrock AgentCore (7 variables, 3 groups) ─────────────────────
    ServiceType.BEDROCK_AGENTCORE: [
        # General
        VariableSchemaEntry(
            name="agent_runtime_name",
            type="string",
            description="Name of the AgentCore runtime",
            group="General",
        ),
        VariableSchemaEntry(
            name="foundation_model",
            type="string",
            description="Foundation model for the agent runtime",
            group="General",
            options=[
                OptionEntry(value="anthropic.claude-v2", label="Anthropic Claude v2"),
                OptionEntry(
                    value="anthropic.claude-3-sonnet-20240229-v1:0",
                    label="Anthropic Claude 3 Sonnet",
                ),
                OptionEntry(
                    value="anthropic.claude-3-haiku-20240307-v1:0",
                    label="Anthropic Claude 3 Haiku",
                ),
                OptionEntry(
                    value="amazon.titan-text-express-v1",
                    label="Amazon Titan Text Express",
                ),
                OptionEntry(
                    value="meta.llama3-8b-instruct-v1:0",
                    label="Meta Llama 3 8B Instruct",
                ),
            ],
        ),
        VariableSchemaEntry(
            name="role_arn",
            type="string",
            description="IAM role ARN for the AgentCore runtime",
            group="General",
        ),
        VariableSchemaEntry(
            name="description",
            type="string",
            description="Description of the agent runtime",
            group="General",
        ),
        # Configuration
        VariableSchemaEntry(
            name="memory_id",
            type="string",
            description="Memory store identifier for session context",
            group="Configuration",
        ),
        VariableSchemaEntry(
            name="idle_session_ttl",
            type="number",
            description="Idle session timeout in seconds",
            default=600,
            group="Configuration",
            validation=ValidationRule(min=60, max=3600),
        ),
        # Metadata
        VariableSchemaEntry(
            name="tags",
            type="map",
            description="Tags to apply to the AgentCore runtime",
            group="Metadata",
        ),
    ],
}
