"""Container log bindings make delivery mode and buffering explicit."""

import re

from pydantic import StrictInt, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule, VisibleWhen

CONTAINER_NAME_PATTERN = r"^[A-Za-z0-9_-]{1,255}$"
STREAM_PREFIX_PATTERN = r"^[A-Za-z0-9_./#-]{1,128}$"


class EcsLogsConfig(BaseConnectionConfig):
    container_name: str = ConnectionField(
        "",
        label="Application container",
        description="Empty selects the container named after the ECS node",
    )
    stream_prefix: str = ConnectionField(
        "ecs",
        label="Log stream prefix",
        validation=ValidationRule(pattern=STREAM_PREFIX_PATTERN),
    )
    mode: str = ConnectionField(
        "non-blocking",
        label="Log delivery mode",
        type="select",
        options=[
            OptionEntry(value="non-blocking", label="Non-blocking"),
            OptionEntry(value="blocking", label="Blocking"),
        ],
        validation=ValidationRule(allowed_values=["non-blocking", "blocking"]),
    )
    buffer_size_mib: StrictInt = ConnectionField(
        10,
        label="Log buffer size (MiB)",
        type="number",
        description="Non-blocking buffer reserves task memory and can lose logs when full",
        validation=ValidationRule(min=1, max=64),
        visible_when=VisibleWhen(field="mode", equals="non-blocking"),
    )

    @field_validator("container_name")
    @classmethod
    def validate_container(cls, value: str) -> str:
        if value and not re.fullmatch(CONTAINER_NAME_PATTERN, value):
            raise ValueError(
                "Use a container name with up to 255 letters, numbers, hyphens, or underscores"
            )
        return value
