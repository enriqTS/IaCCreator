"""Data models for the API Gateway generator configuration."""


from pydantic import BaseModel


class RouteConfig(BaseModel):
    """Configuration for an API Gateway route.

    Defines an HTTP or WebSocket route with its method, path,
    and optional authorizer/integration associations.
    """

    method: str
    """HTTP method: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, or ANY."""

    path: str
    """Route path starting with /, e.g. /users/{id}."""

    authorizer_name: str | None = None
    """Name of the authorizer to attach to this route."""

    integration_name: str | None = None
    """Name of the integration to attach to this route."""


class StageConfig(BaseModel):
    """Configuration for an API Gateway deployment stage.

    Defines stage settings including auto-deploy, variables,
    throttling, and access logging.
    """

    name: str
    """Stage name, e.g. '$default', 'dev', 'prod'."""

    auto_deploy: bool = True
    """Whether to auto-deploy changes to this stage."""

    stage_variables: dict[str, str] | None = None
    """Key-value map of stage variables (max 50 entries)."""

    throttling_burst_limit: int | None = None
    """Default burst limit for the stage (1-5000)."""

    throttling_rate_limit: float | None = None
    """Default rate limit for the stage (1.0-10000.0)."""

    access_logging_enabled: bool = False
    """Whether access logging is enabled for this stage."""

    access_log_retention_days: int = 30
    """CloudWatch log group retention in days."""

    access_log_format: str | None = None
    """Custom access log format string. Uses default format if not provided."""

    route_throttling: list[dict] | None = None
    """Per-route throttling overrides: [{route_key, burst, rate}]."""


class AuthorizerConfig(BaseModel):
    """Configuration for an API Gateway authorizer.

    Supports JWT, Lambda REQUEST, and Cognito User Pools authorizer types.
    """

    name: str
    """Unique authorizer name within the API."""

    type: str
    """Authorizer type: 'JWT', 'REQUEST', or 'COGNITO_USER_POOLS'."""

    # JWT fields
    issuer: str | None = None
    """JWT issuer URL. Required for JWT and Cognito authorizers."""

    audience: list[str] | None = None
    """JWT audience values. Required for JWT and Cognito authorizers."""

    # Lambda fields
    lambda_arn: str | None = None
    """Lambda function ARN for REQUEST authorizers."""

    payload_format_version: str = "2.0"
    """Payload format version for Lambda authorizers: '1.0' or '2.0'."""

    # Cognito fields
    cognito_user_pool_endpoint: str | None = None
    """Cognito User Pool endpoint URL."""

    cognito_client_ids: list[str] | None = None
    """Cognito User Pool client IDs used as audience."""


class IntegrationConfig(BaseModel):
    """Configuration for an API Gateway integration.

    Supports AWS_PROXY (Lambda), HTTP_PROXY, and HTTP integration types.
    """

    name: str
    """Unique integration name within the API."""

    type: str
    """Integration type: 'AWS_PROXY', 'HTTP_PROXY', or 'HTTP'."""

    uri: str | None = None
    """Integration URI. Required for HTTP and HTTP_PROXY types."""

    method: str | None = None
    """HTTP method for HTTP/HTTP_PROXY integrations."""

    vpc_link_name: str | None = None
    """VPC link name for VPC_LINK connection type."""

    payload_format_version: str = "2.0"
    """Payload format version: '1.0' or '2.0'."""


class VPCLinkConfig(BaseModel):
    """Configuration for an API Gateway VPC link.

    Enables private integrations to resources inside a VPC.
    """

    name: str
    """Unique VPC link name."""

    subnet_ids: list[str]
    """Subnet IDs for the VPC link (1-3 entries)."""

    security_group_ids: list[str]
    """Security group IDs for the VPC link (1-5 entries)."""


class CustomDomainConfig(BaseModel):
    """Configuration for an API Gateway custom domain.

    Defines the domain name and ACM certificate for TLS.
    """

    domain_name: str
    """The custom domain name, e.g. 'api.example.com'."""

    certificate_arn: str
    """ARN of the ACM certificate for TLS."""


class ValidationError(BaseModel):
    """A validation error produced by the APIGatewayValidator.

    Contains structured information about what failed validation.
    """

    field: str
    """Dot-notation path to the invalid field, e.g. 'routes[0].method'."""

    message: str
    """Human-readable error description."""

    code: str
    """Machine-readable error code, e.g. 'INVALID_METHOD'."""
