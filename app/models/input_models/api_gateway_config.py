"""API Gateway-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class ApiGatewayConfig(BaseServiceConfig):
    """API Gateway-specific configuration."""

    service_type: Literal[ServiceType.API_GATEWAY] = ServiceType.API_GATEWAY
    protocol_type: str | None = None
    cors_configuration: dict | None = None
    disable_execute_api_endpoint: bool | None = None
    route_selection_expression: str | None = None
    routes: list[dict] | None = None
    stages: list[dict] | None = None
    authorizers: list[dict] | None = None
    custom_domain: dict | None = None
    vpc_links: list[dict] | None = None
    integrations: list[dict] | None = None
    api_key_required: bool | None = None
    throttling_burst_limit: int | None = None
    throttling_rate_limit: float | None = None
    access_log_retention_days: int | None = None
    access_log_format: str | None = None
