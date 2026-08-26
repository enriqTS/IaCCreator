"""AWS AppSync GraphQL API configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField, VisibleWhen


class AppSyncConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.APPSYNC] = ServiceType.APPSYNC
    authentication_type: str = TerraformField(
        "API_KEY",
        description="Default API authentication type",
        options=[
            OptionEntry(value="API_KEY", label="API key"),
            OptionEntry(value="AWS_IAM", label="AWS IAM"),
        ],
    )
    create_api_key: bool = TerraformField(
        True,
        description="Create an API key",
        visible_when=VisibleWhen(field="authentication_type", equals="API_KEY"),
    )
    schema_definition: str | None = TerraformField(
        None, description="Optional GraphQL schema document"
    )
    xray_enabled: bool = TerraformField(True, description="Enable AWS X-Ray tracing")
