from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class KendraConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.KENDRA] = ServiceType.KENDRA
    index_name: str = TerraformField("search-index", description="Kendra index name")
    role_arn: str = TerraformField("", description="IAM role ARN used by Kendra")
    edition: str = TerraformField(
        "DEVELOPER_EDITION", description="Kendra index edition"
    )
