"""AWS CodeArtifact domain and repository configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CodeArtifactConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.CODEARTIFACT] = ServiceType.CODEARTIFACT
    domain_name: str = TerraformField(
        "artifact-domain", description="CodeArtifact domain name"
    )
    repository_name: str = TerraformField(
        "packages", description="CodeArtifact repository name"
    )
    description: str | None = TerraformField(None, description="Repository description")
    kms_key: str | None = TerraformField(
        None, description="KMS key ARN for domain encryption"
    )
    upstream_repository_names: list[str] = TerraformField(
        [], description="Repositories used as upstream sources"
    )
