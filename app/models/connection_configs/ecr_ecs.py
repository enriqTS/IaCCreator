import re

from pydantic import StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.ecr_image import IMAGE_VERSION_PATTERN
from app.models.input_models._metadata import ValidationRule
from app.models.input_models.ecs_containers import CONTAINER_PATTERN


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
