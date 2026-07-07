"""API Gateway-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
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
    api_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the API Gateway",
    )
    protocol_type: str | None = TerraformField(
        "HTTP",
        group="General",
        description="API protocol type",
        options=[
            OptionEntry(value="HTTP", label="HTTP"),
            OptionEntry(value="WEBSOCKET", label="WebSocket"),
            OptionEntry(value="REST", label="REST"),
        ],
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the API",
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
        visible_when=VisibleWhen(
            field="authorizer_type", equals="COGNITO_USER_POOLS"
        ),
    )
    cognito_client_ids: list[str] | None = TerraformField(
        None,
        group="Authorizers",
        description="List of Cognito User Pool client IDs",
        visible_when=VisibleWhen(
            field="authorizer_type", equals="COGNITO_USER_POOLS"
        ),
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
