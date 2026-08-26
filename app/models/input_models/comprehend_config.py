from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ComprehendConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.COMPREHEND] = ServiceType.COMPREHEND
    classifier_name: str = TerraformField(
        "document-classifier", description="Document classifier name"
    )
    data_access_role_arn: str = TerraformField(
        "", description="IAM role ARN used to access training data"
    )
    language_code: str = TerraformField("en", description="Training language code")
    training_data_s3_uri: str = TerraformField(
        "", description="S3 URI containing labeled training data"
    )
    output_data_s3_uri: str = TerraformField(
        "", description="S3 URI receiving classifier output"
    )
