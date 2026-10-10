from pydantic import StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.ecr_image import IMAGE_VERSION_PATTERN
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models._metadata import OptionEntry, ValidationRule

KUBERNETES_LABEL_PATTERN = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
DEPLOYMENT_PATTERN = r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$"
PULL_ROLE_TYPES = ["node", "fargate"]


class EcrEksConfig(BaseConnectionConfig):
    namespace: StrictStr = ConnectionField(
        "default",
        label="Kubernetes namespace",
        validation=ValidationRule(pattern=KUBERNETES_LABEL_PATTERN),
    )
    deployment_name: StrictStr = ConnectionField(
        ...,
        label="Existing Deployment",
        validation=ValidationRule(pattern=DEPLOYMENT_PATTERN),
    )
    container_name: StrictStr = ConnectionField(
        "app",
        label="Existing application container",
        validation=ValidationRule(pattern=KUBERNETES_LABEL_PATTERN),
    )
    image_version: StrictStr = ConnectionField(
        "latest",
        label="Image tag or digest",
        validation=ValidationRule(pattern=IMAGE_VERSION_PATTERN),
    )
    pull_role_arn: StrictStr = ConnectionField(
        ...,
        label="Existing image pull role ARN",
        description="EC2 worker role or Fargate pod execution role, already used by the workload's compute",
        validation=ValidationRule(pattern=ROLE_ARN_PATTERN),
    )
    pull_role_type: StrictStr = ConnectionField(
        "node",
        label="Image pull role type",
        type="select",
        options=[
            OptionEntry(value="node", label="EC2 worker node"),
            OptionEntry(value="fargate", label="Fargate pod execution"),
        ],
        validation=ValidationRule(allowed_values=PULL_ROLE_TYPES),
    )

    @field_validator("deployment_name")
    @classmethod
    def valid_deployment(cls, value: str) -> str:
        if len(value) > 253 or any(
            not part or len(part) > 63 or part.startswith("-") or part.endswith("-")
            for part in value.split(".")
        ):
            raise ValueError("Use a Kubernetes DNS subdomain deployment name")
        return value
