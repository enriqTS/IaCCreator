from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class LexConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.LEX] = ServiceType.LEX
    bot_name: str = TerraformField("assistant", description="Lex bot name")
    role_arn: str = TerraformField("", description="IAM role ARN used by Lex")
    idle_session_ttl_in_seconds: int = TerraformField(
        300, description="Idle session timeout in seconds"
    )
    child_directed: bool = TerraformField(
        False, description="Whether the bot is directed at children"
    )
