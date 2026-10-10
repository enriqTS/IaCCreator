import re

from pydantic import StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule
from app.models.input_models.ecs_containers import CONTAINER_PATTERN

IMAGE_VERSION_PATTERN = r"^([A-Za-z0-9_][A-Za-z0-9_.-]{0,127}|sha256:[0-9a-f]{64})$"
REPOSITORY_PATTERN = (
    r"^[a-z0-9]+(([.]|_|__|-+)[a-z0-9]+)*(/[a-z0-9]+(([.]|_|__|-+)[a-z0-9]+)*)*$"
)
PRIVATE_ECR_PATTERN = r"^[0-9]{12}[.]dkr[.-]ecr[.-]"


class EcrEcsConfig(BaseConnectionConfig):
    container_name: StrictStr = ConnectionField(
        "",
        label="Application container",
        description="Empty selects the container named after the ECS node",
    )
    image_version: StrictStr = ConnectionField(
        "latest",
        label="Image tag or digest",
        description="Existing tag or sha256 digest; images must be pushed before deploying tasks",
        validation=ValidationRule(pattern=IMAGE_VERSION_PATTERN),
    )

    @field_validator("container_name")
    @classmethod
    def valid_container(cls, value: str) -> str:
        if value and not re.fullmatch(CONTAINER_PATTERN, value):
            raise ValueError("Select a bounded literal application container name")
        return value
