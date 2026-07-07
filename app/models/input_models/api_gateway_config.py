"""API Gateway-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class ApiGatewayConfig(BaseServiceConfig):
    """API Gateway-specific configuration."""

    service_type: Literal[ServiceType.API_GATEWAY] = ServiceType.API_GATEWAY
    protocol_type: Optional[str] = None
    cors_configuration: Optional[dict] = None
    disable_execute_api_endpoint: Optional[bool] = None
    route_selection_expression: Optional[str] = None
    routes: Optional[list[dict]] = None
    stages: Optional[list[dict]] = None
    authorizers: Optional[list[dict]] = None
    custom_domain: Optional[dict] = None
    vpc_links: Optional[list[dict]] = None
    integrations: Optional[list[dict]] = None
    api_key_required: Optional[bool] = None
    throttling_burst_limit: Optional[int] = None
    throttling_rate_limit: Optional[float] = None
    access_log_retention_days: Optional[int] = None
    access_log_format: Optional[str] = None
