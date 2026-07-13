"""API Gateway-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._connections import ConnectionInput
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
    VisibleWhen,
)


class ApiGatewayConfig(BaseServiceConfig):
    """API Gateway-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.API_GATEWAY] = ServiceType.API_GATEWAY

    # ─── General ───────────────────────────────────────────────────────────
    api_name: str = TerraformField(
        ...,
        group="General",
        description="Name of the API Gateway",
    )
    protocol_type: str = TerraformField(
        ...,
        group="General",
        description="API protocol type",
        options=[
            OptionEntry(value="HTTP", label="HTTP"),
            OptionEntry(value="WEBSOCKET", label="WebSocket"),
        ],
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the API",
    )
    api_key_selection_expression: str | None = TerraformField(
        None,
        group="General",
        description="API key selection expression for the API",
    )
    ip_address_type: str | None = TerraformField(
        None,
        group="General",
        description="IP address type for the API endpoint",
        options=[
            OptionEntry(value="ipv4", label="IPv4"),
            OptionEntry(value="dualstack", label="Dualstack (IPv4 + IPv6)"),
        ],
    )
    version: str | None = TerraformField(
        None,
        group="General",
        description="Version identifier for the API",
    )
    body: str | None = TerraformField(
        None,
        group="General",
        description="OpenAPI specification body for the API",
    )
    fail_on_warnings: bool | None = TerraformField(
        None,
        group="General",
        description="Whether to roll back the API creation when a warning is encountered",
    )

    # ─── Routes ────────────────────────────────────────────────────────────
    route_method: str | None = TerraformField(
        "ANY",
        group="Routes",
        description="HTTP method for the route",
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
    )
    route_path: str | None = TerraformField(
        None,
        group="Routes",
        description="Route path (e.g., /users/{id})",
    )
    route_selection_expression: str | None = TerraformField(
        None,
        group="Routes",
        description="Route selection expression for WebSocket APIs",
        visible_when=VisibleWhen(field="protocol_type", equals="WEBSOCKET"),
    )
    authorization_type: str | None = TerraformField(
        None,
        group="Routes",
        description="Authorization type for the route",
        options=[
            OptionEntry(value="NONE", label="None"),
            OptionEntry(value="JWT", label="JWT"),
            OptionEntry(value="AWS_IAM", label="AWS IAM"),
            OptionEntry(value="CUSTOM", label="Custom"),
        ],
    )
    authorization_scopes: list[str] | None = TerraformField(
        None,
        group="Routes",
        description="Authorization scopes for the route",
    )
    operation_name: str | None = TerraformField(
        None,
        group="Routes",
        description="Operation name for the route",
    )
    model_selection_expression: str | None = TerraformField(
        None,
        group="Routes",
        description="Model selection expression for the route",
    )
    route_response_selection_expression: str | None = TerraformField(
        None,
        group="Routes",
        description="Route response selection expression",
    )

    # ─── Stages ────────────────────────────────────────────────────────────
    stage_name: str | None = TerraformField(
        None,
        group="Stages",
        description="Name of the deployment stage (e.g., $default, dev, prod)",
    )
    auto_deploy: bool | None = TerraformField(
        True,
        group="Stages",
        description="Whether to auto-deploy changes to this stage",
    )
    stage_variables: dict[str, str] | None = TerraformField(
        None,
        group="Stages",
        description="Stage variables as key-value pairs (max 50 entries)",
    )
    access_log_destination_arn: str | None = TerraformField(
        None,
        group="Stages",
        description="ARN of the CloudWatch log group for access logging",
    )
    access_log_format: str | None = TerraformField(
        None,
        group="Stages",
        description="Access log format string for the stage",
    )
    default_route_data_trace_enabled: bool | None = TerraformField(
        None,
        group="Stages",
        description="Whether data trace logging is enabled for the default route",
    )
    default_route_detailed_metrics_enabled: bool | None = TerraformField(
        None,
        group="Stages",
        description="Whether detailed metrics are enabled for the default route",
    )
    default_route_logging_level: str | None = TerraformField(
        None,
        group="Stages",
        description="Logging level for the default route",
        options=[
            OptionEntry(value="ERROR", label="ERROR"),
            OptionEntry(value="INFO", label="INFO"),
            OptionEntry(value="OFF", label="OFF"),
        ],
    )
    default_route_throttling_burst_limit: int | None = TerraformField(
        None,
        group="Stages",
        description="Throttling burst limit for the default route",
    )
    default_route_throttling_rate_limit: float | None = TerraformField(
        None,
        group="Stages",
        description="Throttling rate limit for the default route",
    )

    # ─── Authorizers ───────────────────────────────────────────────────────
    authorizer_type: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Type of authorizer to attach to the API",
        options=[
            OptionEntry(value="JWT", label="JWT"),
            OptionEntry(value="REQUEST", label="Lambda (REQUEST)"),
            OptionEntry(value="COGNITO_USER_POOLS", label="Cognito User Pools"),
        ],
    )
    jwt_issuer: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Issuer URL for the JWT authorizer",
        visible_when=VisibleWhen(field="authorizer_type", equals="JWT"),
    )
    jwt_audience: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Audience value(s) for the JWT authorizer",
        visible_when=VisibleWhen(field="authorizer_type", equals="JWT"),
    )
    lambda_authorizer_uri: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Lambda function invoke ARN for the REQUEST authorizer",
        visible_when=VisibleWhen(field="authorizer_type", equals="REQUEST"),
    )
    authorizer_payload_format_version: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Payload format version for the Lambda authorizer",
        visible_when=VisibleWhen(field="authorizer_type", equals="REQUEST"),
        options=[
            OptionEntry(value="1.0", label="1.0"),
            OptionEntry(value="2.0", label="2.0"),
        ],
    )
    cognito_user_pool_endpoint: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Cognito User Pool endpoint URL",
        visible_when=VisibleWhen(field="authorizer_type", equals="COGNITO_USER_POOLS"),
    )
    cognito_client_ids: list[str] | None = TerraformField(
        None,
        group="Authorizers",
        description="List of Cognito User Pool client IDs",
        visible_when=VisibleWhen(field="authorizer_type", equals="COGNITO_USER_POOLS"),
    )
    authorizer_result_ttl_in_seconds: int | None = TerraformField(
        None,
        group="Authorizers",
        description="Time to live (TTL) for cached authorizer results in seconds",
        validation=ValidationRule(min=0, max=3600),
    )
    enable_simple_responses: bool | None = TerraformField(
        None,
        group="Authorizers",
        description="Whether to enable simple responses for the authorizer",
    )
    authorizer_credentials_arn: str | None = TerraformField(
        None,
        group="Authorizers",
        description="Credentials ARN for the authorizer",
    )
    identity_sources: list[str] | None = TerraformField(
        None,
        group="Authorizers",
        description="Identity sources for the authorizer",
    )

    # ─── Custom Domain ─────────────────────────────────────────────────────
    custom_domain_name: str | None = TerraformField(
        None,
        group="Custom Domain",
        description="Custom domain name for the API (e.g., api.example.com)",
    )
    certificate_arn: str | None = TerraformField(
        None,
        group="Custom Domain",
        description="ARN of the ACM certificate for the custom domain",
    )
    endpoint_type: str | None = TerraformField(
        None,
        group="Custom Domain",
        description="Endpoint type for the custom domain",
        options=[
            OptionEntry(value="REGIONAL", label="Regional"),
        ],
    )
    security_policy: str | None = TerraformField(
        None,
        group="Custom Domain",
        description="TLS security policy for the custom domain",
        options=[
            OptionEntry(value="TLS_1_2", label="TLS 1.2"),
        ],
    )
    mutual_tls_truststore_uri: str | None = TerraformField(
        None,
        group="Custom Domain",
        description="S3 URI of the truststore for mutual TLS authentication",
    )
    mutual_tls_truststore_version: str | None = TerraformField(
        None,
        group="Custom Domain",
        description="Version of the truststore for mutual TLS authentication",
    )
    mutual_tls_authentication: dict | None = TerraformField(
        None,
        group="Custom Domain",
        description="Mutual TLS authentication configuration",
    )

    # ─── Integrations ──────────────────────────────────────────────────────
    integration_type: str | None = TerraformField(
        None,
        group="Integrations",
        description="Type of backend integration",
        options=[
            OptionEntry(value="AWS_PROXY", label="AWS Lambda (AWS_PROXY)"),
            OptionEntry(value="HTTP_PROXY", label="HTTP Proxy (HTTP_PROXY)"),
            OptionEntry(value="HTTP", label="HTTP Custom (HTTP)"),
        ],
    )
    integration_uri: str | None = TerraformField(
        None,
        group="Integrations",
        description="URI of the integration target",
    )
    integration_method: str | None = TerraformField(
        None,
        group="Integrations",
        description="HTTP method for the integration (required for HTTP_PROXY and HTTP)",
        visible_when=VisibleWhen(field="integration_type", equals="HTTP_PROXY"),
    )
    connection_type: str | None = TerraformField(
        None,
        group="Integrations",
        description="Connection type for the integration",
        options=[
            OptionEntry(value="INTERNET", label="Internet"),
            OptionEntry(value="VPC_LINK", label="VPC Link"),
        ],
    )
    connection_id: str | None = TerraformField(
        None,
        group="Integrations",
        description="Connection ID for VPC link integrations",
    )
    content_handling_strategy: str | None = TerraformField(
        None,
        group="Integrations",
        description="Content handling strategy for the integration",
        options=[
            OptionEntry(value="CONVERT_TO_BINARY", label="Convert to Binary"),
            OptionEntry(value="CONVERT_TO_TEXT", label="Convert to Text"),
        ],
    )
    credentials_arn: str | None = TerraformField(
        None,
        group="Integrations",
        description="Credentials ARN for the integration",
    )
    passthrough_behavior: str | None = TerraformField(
        None,
        group="Integrations",
        description="Passthrough behavior for the integration",
        options=[
            OptionEntry(value="WHEN_NO_MATCH", label="When No Match"),
            OptionEntry(value="WHEN_NO_TEMPLATES", label="When No Templates"),
            OptionEntry(value="NEVER", label="Never"),
        ],
    )
    payload_format_version: str | None = TerraformField(
        None,
        group="Integrations",
        description="Payload format version for the integration",
        options=[
            OptionEntry(value="1.0", label="1.0"),
            OptionEntry(value="2.0", label="2.0"),
        ],
    )
    timeout_milliseconds: int | None = TerraformField(
        None,
        group="Integrations",
        description="Integration timeout in milliseconds",
        validation=ValidationRule(min=50, max=30000),
    )
    tls_server_name_to_verify: str | None = TerraformField(
        None,
        group="Integrations",
        description="TLS server name to verify for the integration",
    )
    integration_subtype: str | None = TerraformField(
        None,
        group="Integrations",
        description="Integration subtype for AWS service integrations",
    )

    # ─── Rate Limiting ─────────────────────────────────────────────────────
    throttling_burst_limit: int | None = TerraformField(
        None,
        group="Rate Limiting",
        description="Maximum number of concurrent requests (burst)",
        validation=ValidationRule(min=1, max=5000),
    )
    throttling_rate_limit: float | None = TerraformField(
        None,
        group="Rate Limiting",
        description="Maximum number of requests per second (steady-state)",
        validation=ValidationRule(min=1.0, max=10000.0),
    )

    # ─── VPC Link ──────────────────────────────────────────────────────────
    vpc_link_name: str | None = TerraformField(
        None,
        group="VPC Link",
        description="Name of the VPC link for private integrations",
    )
    vpc_link_subnet_ids: list[str] | None = TerraformField(
        None,
        group="VPC Link",
        description="List of subnet IDs for the VPC link (1-3 entries)",
    )
    vpc_link_security_group_ids: list[str] | None = TerraformField(
        None,
        group="VPC Link",
        description="List of security group IDs for the VPC link (1-5 entries)",
    )

    # ─── Metadata ──────────────────────────────────────────────────────────
    cors_configuration: dict | None = TerraformField(
        None,
        group="Metadata",
        description="CORS configuration for the API",
    )
    disable_execute_api_endpoint: bool | None = TerraformField(
        False,
        group="Metadata",
        description="Disable the default execute-api endpoint",
    )
    api_key_required: bool | None = TerraformField(
        False,
        group="Metadata",
        description="Whether API key is required for routes",
    )
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the API Gateway",
    )

    # ─── Generator-facing fields (not Terraform variables) ─────────────────
    # These fields support the HCL generator's list-based API for complex
    # nested configurations. They are NOT exposed as Terraform variables.
    routes: list[dict] | None = None
    stages: list[dict] | None = None
    authorizers: list[dict] | None = None
    api_keys: list[dict] | None = None
    custom_domain: dict | None = None
    vpc_links: list[dict] | None = None
    integrations: list[dict] | None = None
    access_log_retention_days: int | None = None

    # ─── Schema Field Order ────────────────────────────────────────────────
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        # General
        "api_name",
        "protocol_type",
        "description",
        "api_key_selection_expression",
        "ip_address_type",
        "version",
        "body",
        "fail_on_warnings",
        # Routes
        "route_method",
        "route_path",
        "route_selection_expression",
        "authorization_type",
        "authorization_scopes",
        "operation_name",
        "model_selection_expression",
        "route_response_selection_expression",
        # Stages
        "stage_name",
        "auto_deploy",
        "stage_variables",
        "access_log_destination_arn",
        "access_log_format",
        "default_route_data_trace_enabled",
        "default_route_detailed_metrics_enabled",
        "default_route_logging_level",
        "default_route_throttling_burst_limit",
        "default_route_throttling_rate_limit",
        # Authorizers
        "authorizer_type",
        "jwt_issuer",
        "jwt_audience",
        "lambda_authorizer_uri",
        "authorizer_payload_format_version",
        "cognito_user_pool_endpoint",
        "cognito_client_ids",
        "authorizer_result_ttl_in_seconds",
        "enable_simple_responses",
        "authorizer_credentials_arn",
        "identity_sources",
        # Custom Domain
        "custom_domain_name",
        "certificate_arn",
        "endpoint_type",
        "security_policy",
        "mutual_tls_truststore_uri",
        "mutual_tls_truststore_version",
        "mutual_tls_authentication",
        # Integrations
        "integration_type",
        "integration_uri",
        "integration_method",
        "connection_type",
        "connection_id",
        "content_handling_strategy",
        "credentials_arn",
        "passthrough_behavior",
        "payload_format_version",
        "timeout_milliseconds",
        "tls_server_name_to_verify",
        "integration_subtype",
        # Rate Limiting
        "throttling_burst_limit",
        "throttling_rate_limit",
        # VPC Link
        "vpc_link_name",
        "vpc_link_subnet_ids",
        "vpc_link_security_group_ids",
        # Metadata
        "cors_configuration",
        "disable_execute_api_endpoint",
        "api_key_required",
        "tags",
    )

    # ─── Connection-Derived Inputs ─────────────────────────────────────────

    @classmethod
    def get_connections_schema(cls) -> list[ConnectionInput]:
        """Declare connection-derived inputs for API Gateway.

        API Gateway receives Lambda invoke ARNs from connected Lambda functions
        for integration configuration.
        """
        return [
            ConnectionInput(
                name="lambda_invoke_arn",
                source_service_type="lambda",
                description="Lambda function invoke ARN for integration",
                tf_variable_name="lambda_invoke_arn",
                connection_role="route_handler",
            ),
        ]
