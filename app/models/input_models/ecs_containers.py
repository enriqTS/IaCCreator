import json

from pydantic import BaseModel, ConfigDict, Field, StrictStr, TypeAdapter

CONTAINER_PATTERN = r"^[A-Za-z0-9_-]{1,255}$"


class EcsContainer(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: StrictStr = Field(pattern=CONTAINER_PATTERN)
    image: StrictStr = Field(min_length=1)


def normalize_containers(value: str) -> str:
    containers = TypeAdapter(list[EcsContainer]).validate_json(value)
    if not containers or len({container.name for container in containers}) != len(
        containers
    ):
        raise ValueError("Provide at least one uniquely named application container")
    return json.dumps(
        [container.model_dump() for container in containers], allow_nan=False
    )
